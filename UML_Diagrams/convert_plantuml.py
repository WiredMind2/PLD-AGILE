#!/usr/bin/env python3
"""
Convert PlantUML files to SVG using Kroki service
"""
import os
import requests
import base64
import zlib
from pathlib import Path

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

def main():
    # Set paths
    script_dir = Path(__file__).parent
    plantuml_dir = script_dir / "plantuml_sources"
    output_dir = plantuml_dir  # Output SVG files in the same directory
    
    if not plantuml_dir.exists():
        print(f"Error: {plantuml_dir} not found!")
        return
    
    # Find all .puml files
    puml_files = list(plantuml_dir.glob("*.puml"))
    
    if not puml_files:
        print("No .puml files found!")
        return
    
    print(f"Found {len(puml_files)} PlantUML files to convert\n")
    print("Using Kroki.io service for conversion...\n")
    
    # Convert each file
    success_count = 0
    failed_files = []
    
    for puml_file in puml_files:
        if convert_puml_to_svg(puml_file, output_dir):
            success_count += 1
        else:
            failed_files.append(puml_file.name)
    
    print(f"\n{'='*50}")
    print(f"Conversion complete: {success_count}/{len(puml_files)} SVG files created")
    print(f"{'='*50}")
    
    if failed_files:
        print(f"\n⚠️  Failed files:")
        for fname in failed_files:
            print(f"   - {fname}")
        print(f"\nNote: Some diagrams may be too complex for the Kroki service.")
        print(f"You can try:")
        print(f"  1. Using PlantUML locally: plantuml -tsvg {' '.join(failed_files)}")
        print(f"  2. Using the PlantUML VS Code extension")
    else:
        print(f"\n✓ All diagrams converted successfully!")

if __name__ == "__main__":
    main()
