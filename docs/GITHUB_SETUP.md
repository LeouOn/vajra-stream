# GitHub Setup Instructions

Follow these steps to upload your Vajra.Stream project to GitHub.

## Step 1: Create GitHub Repository

1. Go to https://github.com
2. Click the **+** icon (top right) → **New repository**
3. Repository name: `vajra-stream`
4. Description: "Digital dharma technology for continuous blessing and healing"
5. Choose: **Public** or **Private** (your preference)
6. **Do NOT** initialize with README (we already have one)
7. Click **Create repository**

## Step 2: Initial Setup (One-time)

Open terminal/command prompt in your project folder and run:

```bash
# Navigate to project directory
cd /path/to/vajra-stream

# Initialize git repository
git init

# Add all files
git add .

# Make first commit
git commit -m "Initial commit: Vajra.Stream MVP - Crystal broadcasting system"

# Add your GitHub repository as remote
# Replace YOUR_USERNAME with your actual GitHub username
git remote add origin https://github.com/YOUR_USERNAME/vajra-stream.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## Step 3: Verify Upload

1. Go to https://github.com/YOUR_USERNAME/vajra-stream
2. You should see all your files
3. README.md will display automatically

## Future Updates

When you make changes:

```bash
# Check what changed
git status

# Add changed files
git add .

# Or add specific files
git add path/to/file.py

# Commit with message
git commit -m "Description of what you changed"

# Push to GitHub
git push
```

## Common Git Commands

```bash
# See what changed
git status

# See commit history
git log

# Undo changes to a file (before commit)
git checkout -- filename.py

# Create a new branch for experimental features
git checkout -b feature-name

# Switch back to main branch
git checkout main

# Merge feature branch into main
git merge feature-name
```

## Troubleshooting

### Authentication Issues

If GitHub asks for credentials and you have 2FA enabled, use a **Personal Access Token** instead of password:

1. GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
2. Generate new token
3. Select scope: `repo` (full control)
4. Copy token (you can't see it again!)
5. Use token as password when git asks

### Already Initialized

If you get "repository already exists" error:

```bash
# Remove existing git folder
rm -rf .git

# Start over from Step 2
```

## Project Structure on GitHub

Your repository will look like:

```
vajra-stream/
├── README.md              ← Displays on main page
├── requirements.txt       ← Python dependencies
├── .gitignore            ← Files git ignores
├── core/                 ← Core systems
├── hardware/             ← Physical interfaces
├── modules/              ← Future expansion
├── knowledge/            ← Reference data
├── scripts/              ← Command-line tools
└── config/               ← Settings
```

## Sharing Your Project

Once on GitHub, share with:
- Link: `https://github.com/YOUR_USERNAME/vajra-stream`
- Clone command: `git clone https://github.com/YOUR_USERNAME/vajra-stream.git`

Anyone can then:
1. Clone your repository
2. Install dependencies: `pip install -r requirements.txt`
3. Run setup: `python scripts/setup_database.py`
4. Start blessing: `python scripts/run_blessing.py`

## License

Consider adding a LICENSE file:
- MIT License (permissive, recommended for spiritual tech)
- GPL (requires derivatives to be open source)
- CC0 (public domain dedication)

Example MIT LICENSE file:

```
MIT License

Copyright (c) 2025 [Your Name]

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

May this technology benefit all beings.
```

## Ready to Share!

Once pushed to GitHub, your sacred technology is preserved and shareable with the world. 🙏
