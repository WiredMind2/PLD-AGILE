#!/usr/bin/env python3
"""
Convert PlantUML files to SVG using Kroki service
Convert PDF files to SVG using PyMuPDF
Update README.md with current Git repository information
"""
import os
import requests
import base64
import zlib
import subprocess
import re
from pathlib import Path
import fitz  # PyMuPDF

def convert_puml_to_svg(puml_file, output_dir):
    """Convert a single PlantUML file to SVG using Kroki"""
    print(f"Converting {puml_file.name} to SVG...")
    
    # Read PlantUML content
    with open(puml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        # Use Kroki.io service with POST (better for larger diagrams)
        kroki_url = "https://kroki.io/plantuml/svg"
        
        # Send diagram content as plain text in request body
        print(f"  Fetching from Kroki...")
        response = requests.post(
            kroki_url,
            data=content.encode('utf-8'),
            headers={'Content-Type': 'text/plain'},
            timeout=30
        )
        response.raise_for_status()
        
        svg_content = response.content.decode('utf-8', errors='ignore')
        
        # Save SVG file directly
        output_file = output_dir / f"{puml_file.stem}.svg"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        file_size = len(svg_content)
        print(f"  ✓ Created {output_file.name} ({file_size:,} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def convert_pdf_to_svg(pdf_file, output_dir):
    """Convert a single PDF file to SVG using PyMuPDF"""
    
    print(f"Converting {pdf_file.name} to SVG...")
    
    try:
        # Open PDF file
        doc = fitz.open(pdf_file)
        
        # Process first page only (assuming single-page diagrams)
        page = doc[0]
        
        # Convert to SVG
        svg_content = page.get_svg_image()
        
        # Save SVG file
        output_file = output_dir / f"{pdf_file.stem}.svg"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(svg_content)
        
        doc.close()
        
        file_size = len(svg_content)
        print(f"  ✓ Created {output_file.name} ({file_size:,} bytes)")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def get_git_info(repo_path):
    """Get current Git repository owner, name, and branch"""
    try:
        # Get current branch
        result = subprocess.run(
            ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        branch = result.stdout.strip()
        
        # Get remote URL
        result = subprocess.run(
            ['git', 'config', '--get', 'remote.origin.url'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()
        
        # Parse owner and repo from URL
        # Handles both HTTPS and SSH URLs
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        match = re.search(r'github\.com[:/](.+?)/(.+?)(\.git)?$', remote_url)
        if match:
            owner = match.group(1)
            repo = match.group(2).replace('.git', '')
            return owner, repo, branch
        else:
            print("⚠️  Could not parse GitHub repository information from remote URL")
            return None, None, None
            
    except subprocess.CalledProcessError as e:
        print(f"⚠️  Error getting Git information: {e}")
        return None, None, None
    except FileNotFoundError:
        print("⚠️  Git not found. Make sure Git is installed and in PATH")
        return None, None, None

def update_readme_urls(readme_path, owner, repo, branch, deliverables_folder="deliverables"):
    """Update all GitHub raw URLs in README.md with current repository info"""
    try:
        with open(readme_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Pattern to match GitHub raw URLs
        # Matches: https://raw.githubusercontent.com/OWNER/REPO/BRANCH/path
        pattern = r'https://raw\.githubusercontent\.com/[^/]+/[^/]+/[^/]+/(deliverables/generated_svgs/[^)]+\.svg)'
        
        # Replace with current repo info
        new_url_template = f'https://raw.githubusercontent.com/{owner}/{repo}/{branch}/\\1'
        updated_content = re.sub(pattern, new_url_template, content)
        
        # Count replacements
        original_urls = re.findall(pattern, content)
        num_updates = len(original_urls)
        
        if num_updates > 0:
            with open(readme_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            print(f"  ✓ Updated {num_updates} GitHub URLs in README.md")
            print(f"    Repository: {owner}/{repo}")
            print(f"    Branch: {branch}")
            return True
        else:
            print("  ℹ️  No GitHub URLs found to update in README.md")
            return False
            
    except Exception as e:
        print(f"  ✗ Error updating README: {e}")
        return False

def main():
    # Set paths
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent  # Go up one level to repo root
    plantuml_dir = script_dir / "plantuml_sources"
    sprint_dir = script_dir / "sprint_diagrams"
    output_dir = script_dir / "generated_svgs"  # Output SVG files in separate directory
    readme_path = script_dir / "README.md"
    
    # Create output directory if it doesn't exist
    output_dir.mkdir(exist_ok=True)
    
    print("="*50)
    print("SVG Generation & README Update Script")
    print("="*50)
    print()
    
    total_success = 0
    total_files = 0
    failed_files = []
    
    # ========== Convert PlantUML files ==========
    if plantuml_dir.exists():
        puml_files = list(plantuml_dir.glob("*.puml"))
        
        if puml_files:
            total_files += len(puml_files)
            print(f"Found {len(puml_files)} PlantUML files to convert")
            print("Using Kroki.io service for conversion...\n")
            
            for puml_file in puml_files:
                if convert_puml_to_svg(puml_file, output_dir):
                    total_success += 1
                else:
                    failed_files.append(puml_file.name)
            
            print()  # Empty line
    
    # ========== Convert PDF files ==========
    if sprint_dir.exists():
        pdf_files = list(sprint_dir.glob("*.pdf"))
        
        if pdf_files:
            total_files += len(pdf_files)
            print(f"Found {len(pdf_files)} PDF files to convert")
            print("Using PyMuPDF for conversion...\n")
            
            for pdf_file in pdf_files:
                if convert_pdf_to_svg(pdf_file, output_dir):
                    total_success += 1
                else:
                    failed_files.append(pdf_file.name)
    
    # ========== Summary ==========
    print(f"\n{'='*50}")
    print(f"Conversion complete: {total_success}/{total_files} files converted")
    print(f"{'='*50}")
    
    if failed_files:
        print(f"\n⚠️  Failed files:")
        for fname in failed_files:
            print(f"   - {fname}")
        print(f"\nNote: Some files may require manual conversion.")
        print(f"For PlantUML files, try:")
        print(f"  1. Using PlantUML locally: plantuml -tsvg <file>")
        print(f"  2. Using the PlantUML VS Code extension")
        print(f"\nFor PDF files, ensure PyMuPDF is installed:")
        print(f"  pip install PyMuPDF")
    else:
        if total_files > 0:
            print(f"\n✓ All files converted successfully!")
        else:
            print(f"\n⚠️  No files found to convert.")
    
    # ========== Update README with Git info ==========
    print(f"\n{'='*50}")
    print("Updating README.md with current Git repository info")
    print(f"{'='*50}\n")
    
    owner, repo, branch = get_git_info(repo_root)
    
    if owner and repo and branch:
        if readme_path.exists():
            update_readme_urls(readme_path, owner, repo, branch, script_dir.name)
        else:
            print(f"  ⚠️  README.md not found at {readme_path}")
    else:
        print("  ⚠️  Skipping README update due to missing Git information")
    
    print(f"\n{'='*50}")
    print("Script completed!")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
