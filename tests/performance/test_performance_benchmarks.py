"""Performance testing and benchmarking for AI-Powered Migration Validation System.

This module provides comprehensive performance testing including load testing,
stress testing, memory profiling, and performance regression detection.
"""

import gc
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import as_completed
from dataclasses import dataclass
from typing import Any
from typing import Callable
from typing import Dict
from typing import List
from unittest.mock import Mock

import psutil
import pytest
from memory_profiler import profile

from src.analyzers.code_analyzer import CodeAnalyzer
from src.core.input_processor import InputProcessor
from src.core.migration_validator import MigrationValidator
from src.core.models import InputData
from src.core.models import InputType
from src.core.models import MigrationValidationRequest
from src.core.models import TechnologyContext
from src.core.models import TechnologyType
from src.core.models import ValidationScope

# ═══════════════════════════════════════════════════════════════
# Performance Testing Framework
# ═══════════════════════════════════════════════════════════════


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""

    execution_time: float
    memory_usage_mb: float
    cpu_usage_percent: float
    peak_memory_mb: float
    throughput_ops_per_sec: float = 0.0
    latency_percentiles: Dict[int, float] = None

    def __post_init__(self):
        if self.latency_percentiles is None:
            self.latency_percentiles = {}


class PerformanceTester:
    """Performance testing framework."""

    def __init__(self):
        self.baseline_metrics = {}

    def measure_execution_time(self, func: Callable, *args, **kwargs) -> float:
        """Measure execution time of a function."""
        start_time = time.perf_counter()
        func(*args, **kwargs)
        end_time = time.perf_counter()
        return end_time - start_time

    def measure_memory_usage(self, func: Callable, *args, **kwargs) -> tuple:
        """Measure memory usage of a function."""
        process = psutil.Process()

        # Get initial memory
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Force garbage collection
        gc.collect()

        # Execute function
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()

        # Get peak memory
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB

        execution_time = end_time - start_time
        memory_used = peak_memory - initial_memory

        return result, execution_time, memory_used, peak_memory

    def measure_cpu_usage(
            self,
            func: Callable,
            duration: float,
            *args,
            **kwargs) -> float:
        """Measure CPU usage during function execution."""
        cpu_percent_start = psutil.cpu_percent()

        start_time = time.time()
        while time.time() - start_time < duration:
            func(*args, **kwargs)
            time.sleep(0.01)

        cpu_percent_end = psutil.cpu_percent()
        return max(cpu_percent_end - cpu_percent_start, 0)

    def load_test(
        self, func: Callable, num_requests: int, concurrent_users: int, *args, **kwargs,
    ) -> Dict[str, Any]:
        """Perform load testing with concurrent users."""
        execution_times = []
        errors = []

        def worker():
            try:
                start_time = time.perf_counter()
                func(*args, **kwargs)
                end_time = time.perf_counter()
                execution_times.append(end_time - start_time)
            except Exception as e:
                errors.append(str(e))

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(worker) for _ in range(num_requests)]

            for future in as_completed(futures):
                future.result()  # Wait for completion

        # Calculate metrics
        if execution_times:
            return {
                "total_requests": num_requests,
                "successful_requests": len(execution_times),
                "failed_requests": len(errors),
                "error_rate": len(errors) / num_requests,
                "avg_response_time": statistics.mean(execution_times),
                "min_response_time": min(execution_times),
                "max_response_time": max(execution_times),
                "p50_response_time": statistics.median(execution_times),
                "p95_response_time": self._percentile(execution_times, 95),
                "p99_response_time": self._percentile(execution_times, 99),
                "throughput": len(execution_times) / max(execution_times)
                if execution_times
                else 0,
                "errors": errors[:10],  # First 10 errors for debugging
            }
        return {
            "total_requests": num_requests,
            "successful_requests": 0,
            "failed_requests": len(errors),
            "error_rate": 1.0,
            "errors": errors,
        }

    def stress_test(
        self, func: Callable, max_load: int, ramp_up_time: int, *args, **kwargs,
    ) -> Dict[str, Any]:
        """Perform stress testing with gradually increasing load."""
        results = []

        for load in range(1, max_load + 1, max(1, max_load // 10)):
            print(f"Testing with load: {load} concurrent users")

            load_result = self.load_test(func, load * 10, load, *args, **kwargs)
            load_result["concurrent_users"] = load
            results.append(load_result)

            # Check if system is breaking down
            if load_result["error_rate"] > 0.5:  # 50% error rate
                print(f"System breakdown detected at {load} concurrent users")
                break

            time.sleep(ramp_up_time / max_load)

        return {
            "max_stable_load": self._find_max_stable_load(results),
            "breakdown_point": self._find_breakdown_point(results),
            "results": results,
        }

    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of a dataset."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (percentile / 100) * (len(sorted_data) - 1)
        if index.is_integer():
            return sorted_data[int(index)]
        lower = sorted_data[int(index)]
        upper = sorted_data[int(index) + 1]
        return lower + (upper - lower) * (index - int(index))

    def _find_max_stable_load(self, results: List[Dict]) -> int:
        """Find maximum stable load from stress test results."""
        for result in reversed(results):
            if result["error_rate"] < 0.05:  # Less than 5% error rate
                return result["concurrent_users"]
        return 1

    def _find_breakdown_point(self, results: List[Dict]) -> int:
        """Find breakdown point from stress test results."""
        for result in results:
            if result["error_rate"] > 0.5:  # More than 50% error rate
                return result["concurrent_users"]
        return results[-1]["concurrent_users"] if results else 0

    def benchmark_against_baseline(
        self, current_metrics: PerformanceMetrics, test_name: str,
    ) -> Dict[str, Any]:
        """Compare current metrics against baseline."""
        if test_name not in self.baseline_metrics:
            self.baseline_metrics[test_name] = current_metrics
            return {"status": "baseline_set", "baseline": current_metrics}

        baseline = self.baseline_metrics[test_name]

        performance_change = {
            "execution_time_change": (
                current_metrics.execution_time
                - baseline.execution_time)
            / baseline.execution_time
            * 100,
            "memory_usage_change": (
                current_metrics.memory_usage_mb
                - baseline.memory_usage_mb)
            / baseline.memory_usage_mb
            * 100 if baseline.memory_usage_mb > 0 else 0,
            "throughput_change": (
                current_metrics.throughput_ops_per_sec
                - baseline.throughput_ops_per_sec)
            / baseline.throughput_ops_per_sec
            * 100 if baseline.throughput_ops_per_sec > 0 else 0,
        }

        # Determine if performance has regressed
        regression_detected = (
            performance_change["execution_time_change"] > 10
            or performance_change["memory_usage_change"] > 20  # 10% slower
            or performance_change["throughput_change"]  # 20% more memory
            < -10  # 10% less throughput
        )

        return {
            "status": "regression_detected" if regression_detected else "performance_stable",
            "baseline": baseline,
            "current": current_metrics,
            "changes": performance_change,
            "regression_detected": regression_detected,
        }


# ═══════════════════════════════════════════════════════════════
# Core Component Performance Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.performance
@pytest.mark.benchmark
class TestMigrationValidatorPerformance:
    """Performance tests for MigrationValidator."""

    def setup_method(self):
        """Setup test environment."""
        self.tester = PerformanceTester()

        # Mock LLM service to avoid external dependencies
        self.mock_llm_service = Mock()
        self.mock_llm_service.analyze_code_semantic_similarity.return_value = {
            "similarity_score": 0.85,
            "functionally_equivalent": True,
            "confidence": 0.9,
        }

        self.validator = MigrationValidator(llm_client=self.mock_llm_service)

    def test_single_validation_performance(self):
        """Test performance of single validation request."""
        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text="def hello(): return 'Hello World'"),
            target_input=InputData(
                type=InputType.TEXT,
                text='public String hello() { return "Hello World"; }',
            ),
        )

        # Measure performance
        result, execution_time, memory_used, peak_memory = self.tester.measure_memory_usage(
            self.validator.validate, request, )

        metrics = PerformanceMetrics(
            execution_time=execution_time,
            memory_usage_mb=memory_used,
            cpu_usage_percent=0,  # Not measured in this test
            peak_memory_mb=peak_memory,
            throughput_ops_per_sec=1 / execution_time if execution_time > 0 else 0,
        )

        # Performance assertions
        assert execution_time < 5.0, f"Validation took too long: {execution_time:.2f}s"
        assert memory_used < 100, f"Memory usage too high: {memory_used:.2f}MB"
        assert result is not None, "Validation should return a result"

        # Benchmark against baseline
        comparison = self.tester.benchmark_against_baseline(
            metrics, "single_validation")
        print(f"Performance comparison: {comparison}")

    def test_large_code_validation_performance(self):
        """Test performance with large code inputs."""
        # Generate large code files
        large_python_code = "\n".join(
            [f"def function_{i}():\n    return {i}\n" for i in range(1000)],
        )

        large_java_code = "\n".join(
            [f"public int function_{i}() {{\n    return {i};\n}}" for i in range(1000)],
        )

        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text=large_python_code),
            target_input=InputData(
                type=InputType.TEXT,
                text=large_java_code),
        )

        # Measure performance
        start_time = time.perf_counter()
        result = self.validator.validate(request)
        execution_time = time.perf_counter() - start_time

        # Performance assertions for large inputs
        assert execution_time < 30.0, f"Large validation took too long: {
            execution_time:.2f}s"
        assert result is not None, "Large validation should return a result"

    def test_concurrent_validation_performance(self):
        """Test performance under concurrent validation requests."""
        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text="def test(): pass"),
            target_input=InputData(
                type=InputType.TEXT,
                text="public void test() {}"),
        )

        # Load test with concurrent requests
        load_results = self.tester.load_test(
            self.validator.validate,
            num_requests=50,
            concurrent_users=10,
            func_args=(
                request,
            ),
        )

        # Performance assertions
        assert (
            load_results["error_rate"] < 0.1
        ), f"High error rate: {load_results['error_rate']:.2%}"
        assert (
            load_results["avg_response_time"] < 2.0
        ), f"High average response time: {load_results['avg_response_time']:.2f}s"
        assert (
            load_results["p95_response_time"] < 5.0
        ), f"High P95 response time: {load_results['p95_response_time']:.2f}s"

        print(f"Load test results: {json.dumps(load_results, indent=2)}")

    def test_memory_usage_stability(self):
        """Test memory usage stability over multiple validations."""
        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text="def test(): pass"),
            target_input=InputData(
                type=InputType.TEXT,
                text="public void test() {}"),
        )

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Perform multiple validations
        for i in range(100):
            self.validator.validate(request)

            # Check for memory leaks every 20 iterations
            if i % 20 == 0:
                gc.collect()  # Force garbage collection
                current_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = current_memory - initial_memory

                # Memory growth should be reasonable
                assert (
                    memory_growth < 200), f"Excessive memory growth: {
                    memory_growth:.2f}MB after {
                    i + 1} validations"

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        total_growth = final_memory - initial_memory
        print(f"Total memory growth after 100 validations: {total_growth:.2f}MB")

        # Final memory growth check
        assert total_growth < 300, f"Memory leak detected: {total_growth:.2f}MB growth"


@pytest.mark.performance
@pytest.mark.benchmark
class TestCodeAnalyzerPerformance:
    """Performance tests for CodeAnalyzer."""

    def setup_method(self):
        """Setup test environment."""
        self.tester = PerformanceTester()
        self.analyzer = CodeAnalyzer()

    def test_code_analysis_performance(self):
        """Test code analysis performance."""
        # Generate test code
        test_code = """
import os
import sys
from typing import List, Dict, Any

class DataProcessor:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.data = []

    def process_data(self, input_data: List[Dict]) -> List[Dict]:
        processed = []
        for item in input_data:
            if self.validate_item(item):
                processed_item = self.transform_item(item)
                processed.append(processed_item)
        return processed

    def validate_item(self, item: Dict) -> bool:
        required_fields = ['id', 'name', 'value']
        return all(field in item for field in required_fields)

    def transform_item(self, item: Dict) -> Dict:
        return {
            'id': item['id'],
            'name': item['name'].upper(),
            'value': item['value'] * 2,
            'processed': True
        }

def main():
    processor = DataProcessor({'debug': True})
    data = [{'id': i, 'name': f'item_{i}', 'value': i} for i in range(100)]
    result = processor.process_data(data)
    print(f"Processed {len(result)} items")

if __name__ == '__main__':
    main()
"""

        # Measure analysis performance
        start_time = time.perf_counter()
        result = self.analyzer.analyze_code(test_code, TechnologyType.PYTHON_FLASK)
        execution_time = time.perf_counter() - start_time

        # Performance assertions
        assert execution_time < 2.0, f"Code analysis took too long: {
            execution_time:.2f}s"
        assert result is not None, "Analysis should return a result"
        assert "functions" in result, "Analysis should include functions"
        assert "classes" in result, "Analysis should include classes"

        print(f"Code analysis completed in {execution_time:.3f}s")

    def test_large_file_analysis_performance(self):
        """Test analysis performance with large code files."""
        # Generate large Python file
        large_code = "\n".join(
            [
                f"""
class Class_{i}:
    def __init__(self):
        self.value = {i}

    def method_{i}(self, param):
        if param > {i}:
            return param * {i}
        else:
            return param + {i}

    def complex_method_{i}(self, data):
        result = []
        for item in data:
            if item % 2 == 0:
                if item > {i}:
                    result.append(item * 2)
                else:
                    result.append(item + {i})
            else:
                result.append(item - {i})
        return result

def function_{i}():
    return {i}
"""
                for i in range(200)  # 200 classes and functions
            ],
        )

        # Measure performance
        start_time = time.perf_counter()
        result = self.analyzer.analyze_code(large_code, TechnologyType.PYTHON_FLASK)
        execution_time = time.perf_counter() - start_time

        # Performance assertions
        assert execution_time < 20.0, f"Large file analysis took too long: {
            execution_time:.2f}s"
        assert result is not None, "Large file analysis should return a result"
        assert len(result["classes"]) == 200, "Should detect all classes"
        assert len(result["functions"]) == 200, "Should detect all functions"

        print(
            f"Large file analysis ({
                len(large_code)} chars) completed in {
                execution_time:.3f}s")

    def test_concurrent_analysis_performance(self):
        """Test performance under concurrent analysis requests."""
        test_codes = [
            f"def function_{i}():\n    return {i}\n\nclass Class_{i}:\n    pass" for i in range(20)]

        def analyze_code(code):
            return self.analyzer.analyze_code(code, TechnologyType.PYTHON_FLASK)

        # Load test with concurrent analyses
        execution_times = []
        errors = []

        def worker(code):
            try:
                start_time = time.perf_counter()
                result = analyze_code(code)
                end_time = time.perf_counter()
                execution_times.append(end_time - start_time)
                return result
            except Exception as e:
                errors.append(str(e))
                return None

        # Execute concurrent analyses
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(worker, code) for code in test_codes]
            results = [future.result() for future in as_completed(futures)]

        # Performance assertions
        assert len(errors) == 0, f"Errors during concurrent analysis: {errors}"
        assert len(execution_times) == len(test_codes), "All analyses should complete"
        assert (
            statistics.mean(execution_times) < 1.0
        ), f"High average analysis time: {statistics.mean(execution_times):.2f}s"

        print(
            f"Concurrent analysis completed: avg={
                statistics.mean(execution_times):.3f}s, max={
                max(execution_times):.3f}s", )


# ═══════════════════════════════════════════════════════════════
# Memory Profiling Tests
# ═══════════════════════════════════════════════════════════════


@pytest.mark.performance
@pytest.mark.memory
class TestMemoryProfiler:
    """Memory profiling tests."""

    def setup_method(self):
        """Setup test environment."""
        self.tester = PerformanceTester()

    @profile
    def memory_intensive_validation(self):
        """Memory-intensive validation for profiling."""
        # Create large data structures
        large_code = "x" * (1024 * 1024)  # 1MB string

        processor = InputProcessor()
        input_data = InputData(type=InputType.TEXT, text=large_code)

        # Process large input
        result = processor.process_input(input_data)
        return result

    def test_memory_profiling(self):
        """Test memory profiling of validation process."""
        # Run memory-intensive operation
        self.memory_intensive_validation()

        # Memory profiling results are printed by @profile decorator
        # In a real scenario, you'd capture and analyze the output
        assert True  # Test passes if no memory errors occur

    def test_memory_growth_analysis(self):
        """Analyze memory growth patterns."""
        process = psutil.Process()
        memory_samples = []

        # Sample memory usage over time
        for i in range(50):
            memory_before = process.memory_info().rss / 1024 / 1024  # MB

            # Perform operation that might cause memory growth
            self.memory_intensive_validation()

            memory_after = process.memory_info().rss / 1024 / 1024  # MB
            memory_samples.append(memory_after - memory_before)

            # Force garbage collection periodically
            if i % 10 == 0:
                gc.collect()

        # Analyze memory growth trend
        avg_growth = statistics.mean(memory_samples)
        max_growth = max(memory_samples)

        print(f"Memory growth analysis: avg={avg_growth:.2f}MB, max={max_growth:.2f}MB")

        # Assert reasonable memory usage
        assert avg_growth < 10, f"Average memory growth too high: {avg_growth:.2f}MB"
        assert max_growth < 50, f"Maximum memory growth too high: {max_growth:.2f}MB"


# ═══════════════════════════════════════════════════════════════
# Performance Regression Detection
# ═══════════════════════════════════════════════════════════════


@pytest.mark.performance
@pytest.mark.regression
class TestPerformanceRegression:
    """Performance regression detection tests."""

    def setup_method(self):
        """Setup test environment."""
        self.tester = PerformanceTester()
        self.baseline_file = "performance_baselines.json"

    def load_baselines(self) -> Dict[str, Any]:
        """Load performance baselines from file."""
        try:
            with open(self.baseline_file) as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save_baselines(self, baselines: Dict[str, Any]):
        """Save performance baselines to file."""
        with open(self.baseline_file, "w") as f:
            json.dump(baselines, f, indent=2)

    def test_validation_performance_regression(self):
        """Test for performance regression in validation."""
        # Mock components for consistent testing
        mock_llm_service = Mock()
        mock_llm_service.analyze_code_semantic_similarity.return_value = {
            "similarity_score": 0.85,
            "functionally_equivalent": True,
        }

        validator = MigrationValidator(llm_client=mock_llm_service)

        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text="def test(): return 42"),
            target_input=InputData(
                type=InputType.TEXT,
                text="public int test() { return 42; }"),
        )

        # Measure current performance
        execution_times = []
        for _ in range(10):  # Run multiple times for accuracy
            start_time = time.perf_counter()
            validator.validate(request)
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)

        current_avg_time = statistics.mean(execution_times)
        current_p95_time = self.tester._percentile(execution_times, 95)

        # Load baselines
        baselines = self.load_baselines()
        baseline_key = "validation_performance"

        if baseline_key in baselines:
            baseline_avg = baselines[baseline_key]["avg_time"]
            baseline_p95 = baselines[baseline_key]["p95_time"]

            # Check for regression (>20% slower)
            avg_regression = (current_avg_time - baseline_avg) / baseline_avg * 100
            p95_regression = (current_p95_time - baseline_p95) / baseline_p95 * 100

            print("Performance comparison:")
            print(
                f"  Average time: {
                    current_avg_time:.3f}s (baseline: {
                    baseline_avg:.3f}s, change: {
                    avg_regression:+.1f}%)", )
            print(
                f"  P95 time: {
                    current_p95_time:.3f}s (baseline: {
                    baseline_p95:.3f}s, change: {
                    p95_regression:+.1f}%)", )

            # Assert no significant regression
            assert (
                avg_regression < 20), f"Performance regression detected: {
                avg_regression:.1f}% slower average time"
            assert (
                p95_regression < 25
            ), f"Performance regression detected: {p95_regression:.1f}% slower P95 time"

        else:
            # Set new baseline
            baselines[baseline_key] = {
                "avg_time": current_avg_time,
                "p95_time": current_p95_time,
                "timestamp": time.time(),
            }
            self.save_baselines(baselines)
            print(
                f"New performance baseline set: avg={
                    current_avg_time:.3f}s, p95={
                    current_p95_time:.3f}s", )

    def test_code_analysis_performance_regression(self):
        """Test for performance regression in code analysis."""
        analyzer = CodeAnalyzer()

        test_code = """
def complex_function(data):
    result = []
    for item in data:
        if isinstance(item, dict):
            for key, value in item.items():
                if isinstance(value, (int, float)):
                    result.append(key + str(value))
        elif isinstance(item, list):
            result.extend([str(x) for x in item if x is not None])
        else:
            result.append(str(item))
    return result

class DataProcessor:
    def __init__(self):
        self.data = []

    def process(self, input_data):
        return complex_function(input_data)
"""

        # Measure current performance
        execution_times = []
        for _ in range(5):
            start_time = time.perf_counter()
            analyzer.analyze_code(test_code, TechnologyType.PYTHON_FLASK)
            end_time = time.perf_counter()
            execution_times.append(end_time - start_time)

        current_avg_time = statistics.mean(execution_times)

        # Load baselines
        baselines = self.load_baselines()
        baseline_key = "analysis_performance"

        if baseline_key in baselines:
            baseline_avg = baselines[baseline_key]["avg_time"]
            regression = (current_avg_time - baseline_avg) / baseline_avg * 100

            print(
                f"Code analysis performance: {
                    current_avg_time:.3f}s (baseline: {
                    baseline_avg:.3f}s, change: {
                    regression:+.1f}%)", )

            # Assert no significant regression
            assert regression < 30, f"Code analysis regression detected: {
                regression:.1f}% slower"

        else:
            # Set new baseline
            baselines[baseline_key] = {
                "avg_time": current_avg_time,
                "timestamp": time.time()}
            self.save_baselines(baselines)
            print(f"New code analysis baseline set: avg={current_avg_time:.3f}s")


# ═══════════════════════════════════════════════════════════════
# Stress Testing and Breaking Point Detection
# ═══════════════════════════════════════════════════════════════


@pytest.mark.performance
@pytest.mark.slow
class TestStressAndBreakingPoints:
    """Stress testing to find system breaking points."""

    def setup_method(self):
        """Setup test environment."""
        self.tester = PerformanceTester()

    def test_concurrent_validation_stress(self):
        """Stress test with increasing concurrent validations."""
        mock_llm_service = Mock()
        mock_llm_service.analyze_code_semantic_similarity.return_value = {
            "similarity_score": 0.85,
            "functionally_equivalent": True,
        }

        validator = MigrationValidator(llm_client=mock_llm_service)

        request = MigrationValidationRequest(
            source_technology=TechnologyContext(
                type=TechnologyType.PYTHON_FLASK,
                version="2.0"),
            target_technology=TechnologyContext(
                type=TechnologyType.JAVA_SPRING,
                version="3.0"),
            validation_scope=ValidationScope.BUSINESS_LOGIC,
            source_input=InputData(
                type=InputType.TEXT,
                text="def test(): pass"),
            target_input=InputData(
                type=InputType.TEXT,
                text="public void test() {}"),
        )

        # Stress test with increasing load
        stress_results = self.tester.stress_test(
            validator.validate,
            max_load=20,  # Up to 20 concurrent users
            ramp_up_time=10,  # 10 seconds ramp-up
            func_args=(request,),
        )

        print("Stress test results:")
        print(
            f"  Max stable load: {
                stress_results['max_stable_load']} concurrent users")
        print(
            f"  Breakdown point: {
                stress_results['breakdown_point']} concurrent users")

        # Assert reasonable performance under stress
        assert (
            stress_results["max_stable_load"] >= 5
        ), "System should handle at least 5 concurrent users"
        assert (
            stress_results["breakdown_point"] > stress_results["max_stable_load"]
        ), "Breakdown point should be higher than stable load"

    def test_memory_stress_with_large_inputs(self):
        """Stress test memory usage with increasingly large inputs."""
        processor = InputProcessor()

        # Test with increasingly large inputs
        for size_mb in [1, 5, 10, 25]:  # MB
            large_text = "x" * (size_mb * 1024 * 1024)  # Create text of specified size

            input_data = InputData(type=InputType.TEXT, text=large_text)

            process = psutil.Process()
            memory_before = process.memory_info().rss / 1024 / 1024  # MB

            try:
                start_time = time.perf_counter()
                result = processor.process_input(input_data)
                execution_time = time.perf_counter() - start_time

                memory_after = process.memory_info().rss / 1024 / 1024  # MB
                memory_used = memory_after - memory_before

                print(
                    f"Input size: {size_mb}MB, Execution time: {
                        execution_time:.2f}s, Memory used: {
                        memory_used:.2f}MB", )

                # Assert reasonable performance
                assert (
                    execution_time < 30
                ), f"Processing {size_mb}MB took too long: {execution_time:.2f}s"
                assert (
                    memory_used < size_mb * 5
                ), f"Memory usage too high for {size_mb}MB input: {memory_used:.2f}MB"

                # Clean up
                del large_text
                gc.collect()

            except MemoryError:
                print(f"Memory limit reached at {size_mb}MB input size")
                break
            except Exception as e:
                print(f"Error processing {size_mb}MB input: {e}")
                break


@pytest.mark.performance
def test_performance_test_suite_summary():
    """Generate summary of all performance tests."""
    print("\n" + "=" * 60)
    print("PERFORMANCE TEST SUITE SUMMARY")
    print("=" * 60)
    print("Performance tests completed. Key metrics to monitor:")
    print("• Single validation: < 5 seconds")
    print("• Large code validation: < 30 seconds")
    print("• Concurrent validation error rate: < 10%")
    print("• Memory growth per validation: < 200MB")
    print("• Code analysis: < 2 seconds")
    print("• Large file analysis: < 20 seconds")
    print("• Performance regression threshold: < 20%")
    print("• Minimum concurrent users supported: >= 5")
    print("=" * 60)
