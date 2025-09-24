#!/bin/bash
set -euo pipefail

# Git History Cleanup Script for Security Remediation
# WARNING: This script rewrites git history and is destructive
# Run only after coordinating with your team and backing up the repository

echo "🚨 GIT HISTORY CLEANUP SCRIPT 🚨"
echo "This script will rewrite git history to remove exposed secrets."
echo "BACKUP YOUR REPOSITORY BEFORE RUNNING THIS SCRIPT!"
echo ""

# Confirm with user
read -p "Have you backed up the repository and coordinated with your team? (yes/no): " confirm
if [[ $confirm != "yes" ]]; then
    echo "❌ Aborting. Please backup and coordinate before running."
    exit 1
fi

# Check if BFG is available
if command -v java &> /dev/null; then
    echo "✅ Java found, BFG method available"
    USE_BFG=true
else
    echo "⚠️ Java not found, using git filter-branch"
    USE_BFG=false
fi

# Create backup branch
echo "📦 Creating backup branch..."
git branch backup-before-cleanup || echo "Backup branch already exists"

if [[ $USE_BFG == true ]]; then
    echo "🧹 Using BFG Repo-Cleaner method..."

    # Download BFG if not present
    if [[ ! -f "bfg-1.14.0.jar" ]]; then
        echo "📥 Downloading BFG Repo-Cleaner..."
        wget https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar
    fi

    # Create secrets replacement file
    cat > secrets.txt << EOF
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==>REMOVED_API_KEY
eyJ0eXAiOiJKV1QiOiJhbGciOiJIUzI1NiJ9==>REMOVED_JWT_TOKEN
abc123def456==>REMOVED_TEST_KEY
ENCRYPTION_KEY==>REMOVED_ENCRYPTION_KEY
EOF

    # Run BFG
    echo "🔄 Running BFG cleanup..."
    java -jar bfg-1.14.0.jar --replace-text secrets.txt

    # Cleanup
    echo "🧽 Final cleanup..."
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive

    # Clean up temporary files
    rm -f secrets.txt bfg-1.14.0.jar

else
    echo "🧹 Using git filter-branch method..."

    # List of files to clean
    FILES_TO_CLEAN=(
        ".env"
        "docs/testing-strategy.md"
        "tests/conftest.py"
        "tests/security/test_api_integration.py"
    )

    for file in "${FILES_TO_CLEAN[@]}"; do
        echo "🔄 Cleaning $file from history..."
        git filter-branch --force --index-filter \
            "git rm --cached --ignore-unmatch '$file'" \
            --prune-empty --tag-name-filter cat -- --all
    done

    # Cleanup refs
    rm -rf .git/refs/original/
    git reflog expire --expire=now --all
    git gc --prune=now --aggressive
fi

echo ""
echo "✅ History cleanup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Review the changes: git log --oneline"
echo "2. Test your application to ensure it still works"
echo "3. Force push (DANGEROUS): git push --force-with-lease --all"
echo "4. Notify your team about the history rewrite"
echo "5. Have team members re-clone the repository"
echo ""
echo "🔐 Security reminders:"
echo "- Rotate the exposed OpenRouter API key"
echo "- Update production secrets with new keys"
echo "- Monitor API usage for suspicious activity"
echo ""
echo "⚠️ If something goes wrong, restore from backup:"
echo "git reset --hard backup-before-cleanup"