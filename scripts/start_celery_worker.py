#!/usr/bin/env python3
"""Celery worker startup script for P001 async processing.
Production-ready worker management with monitoring.
"""

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import List
from typing import Optional

from src.core.config import get_validation_config
from src.core.logging import logger

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class CeleryWorkerManager:
    """Manage Celery workers for async validation processing."""

    def __init__(self):
        self.config = get_validation_config()
        self.workers: List[subprocess.Popen] = []
        self.running = False

    def start_workers(
        self,
        worker_count: Optional[int] = None,
        concurrency: Optional[int] = None,
        queues: Optional[List[str]] = None,
    ) -> None:
        """Start Celery workers."""
        worker_count = worker_count or self._get_optimal_worker_count()
        concurrency = concurrency or self.config.settings.celery_worker_concurrency
        queues = queues or ["default", "validation", "analysis", "comparison"]

        logger.info(
            "Starting Celery workers",
            worker_count=worker_count,
            concurrency=concurrency,
            queues=queues,
        )

        # Start multiple worker processes
        for i in range(worker_count):
            worker_name = f"worker_{i + 1}"
            queue_list = ",".join(queues)

            cmd = [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "src.services.task_queue.celery_app",
                "worker",
                "--hostname",
                f"{worker_name}@%h",
                "--queues",
                queue_list,
                "--concurrency",
                str(concurrency),
                "--loglevel",
                "info",
                "--without-gossip",
                "--without-mingle",
                "--without-heartbeat",
            ]

            # Add environment variables
            env = os.environ.copy()
            env.update(
                {"PYTHONPATH": str(project_root), "CELERY_WORKER_NAME": worker_name}
            )

            try:
                process = subprocess.Popen(
                    cmd,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    universal_newlines=True,
                )

                self.workers.append(process)
                logger.info(f"Started worker {worker_name}", pid=process.pid)

            except Exception as e:
                logger.error(f"Failed to start worker {worker_name}", error=str(e))

        self.running = True
        self._setup_signal_handlers()

    def stop_workers(self) -> None:
        """Stop all workers gracefully."""
        logger.info("Stopping Celery workers", worker_count=len(self.workers))

        for i, worker in enumerate(self.workers):
            try:
                # Send SIGTERM for graceful shutdown
                worker.terminate()

                # Wait for graceful shutdown
                try:
                    worker.wait(timeout=30)
                    logger.info(f"Worker {i + 1} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    worker.kill()
                    worker.wait()
                    logger.warning(f"Worker {i + 1} force killed")

            except Exception as e:
                logger.error(f"Error stopping worker {i + 1}", error=str(e))

        self.workers.clear()
        self.running = False

    def restart_workers(self) -> None:
        """Restart all workers."""
        logger.info("Restarting Celery workers")
        self.stop_workers()
        self.start_workers()

    def get_worker_status(self) -> List[dict]:
        """Get status of all workers."""
        status = []

        for i, worker in enumerate(self.workers):
            worker_status = {
                "name": f"worker_{i + 1}",
                "pid": worker.pid,
                "running": worker.poll() is None,
                "return_code": worker.returncode,
            }
            status.append(worker_status)

        return status

    def monitor_workers(self) -> None:
        """Monitor workers and restart if needed."""
        logger.info("Starting worker monitoring")

        try:
            import time

            while self.running:
                # Check worker health
                dead_workers = []

                for i, worker in enumerate(self.workers):
                    if worker.poll() is not None:  # Worker died
                        logger.error(
                            f"Worker {i + 1} died", return_code=worker.returncode
                        )
                        dead_workers.append(i)

                # Restart dead workers
                for worker_idx in reversed(dead_workers):
                    self._restart_single_worker(worker_idx)

                time.sleep(10)  # Check every 10 seconds

        except KeyboardInterrupt:
            logger.info("Worker monitoring interrupted")
        except Exception as e:
            logger.error("Worker monitoring error", error=str(e))

    def _get_optimal_worker_count(self) -> int:
        """Determine optimal number of workers."""
        import multiprocessing

        cpu_count = multiprocessing.cpu_count()

        # Use 2 workers per CPU core, but cap at 8 workers
        optimal_workers = min(cpu_count * 2, 8)

        # Ensure at least 1 worker
        return max(optimal_workers, 1)

    def _restart_single_worker(self, worker_idx: int) -> None:
        """Restart a single worker."""
        if worker_idx < len(self.workers):
            old_worker = self.workers[worker_idx]

            # Clean up old worker
            try:
                old_worker.kill()
                old_worker.wait()
            except BaseException:
                pass

            # Start new worker
            worker_name = f"worker_{worker_idx + 1}"
            cmd = [
                sys.executable,
                "-m",
                "celery",
                "-A",
                "src.services.task_queue.celery_app",
                "worker",
                "--hostname",
                f"{worker_name}@%h",
                "--queues",
                "default,validation,analysis,comparison",
                "--concurrency",
                str(self.config.settings.celery_worker_concurrency),
                "--loglevel",
                "info",
            ]

            env = os.environ.copy()
            env.update(
                {"PYTHONPATH": str(project_root), "CELERY_WORKER_NAME": worker_name}
            )

            try:
                new_worker = subprocess.Popen(cmd, env=env)
                self.workers[worker_idx] = new_worker
                logger.info(f"Restarted worker {worker_name}", pid=new_worker.pid)
            except Exception as e:
                logger.error(f"Failed to restart worker {worker_name}", error=str(e))

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down workers")
            self.stop_workers()
            sys.exit(0)

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)


def main():
    """Main entry point for worker management."""
    import argparse

    parser = argparse.ArgumentParser(description="Celery Worker Manager")
    parser.add_argument("--workers", "-w", type=int, help="Number of worker processes")
    parser.add_argument("--concurrency", "-c", type=int, help="Concurrency per worker")
    parser.add_argument("--queues", "-q", nargs="+", help="Queues to process")
    parser.add_argument(
        "--monitor", "-m", action="store_true", help="Enable worker monitoring"
    )
    parser.add_argument("--daemon", "-d", action="store_true", help="Run as daemon")

    args = parser.parse_args()

    # Initialize manager
    manager = CeleryWorkerManager()

    try:
        # Start workers
        manager.start_workers(
            worker_count=args.workers, concurrency=args.concurrency, queues=args.queues
        )

        if args.monitor:
            # Monitor workers
            manager.monitor_workers()
        else:
            # Wait for interrupt
            logger.info("Workers started. Press Ctrl+C to stop.")

            try:
                # Keep main process alive
                import time

                while manager.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutting down...")

    except Exception as e:
        logger.error("Worker manager error", error=str(e))

    finally:
        manager.stop_workers()


if __name__ == "__main__":
    main()
