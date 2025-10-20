#!/usr/bin/env python3
"""
Convert PlantUML files to SVG images using PlantUML server
"""
import os
import requests
import zlib
import base64
from pathlib import Path

def plantuml_encode(plantuml_text):
    """Encode PlantUML text for URL"""
    zlibbed_str = zlib.compress(plantuml_text.encode('utf-8'))
    compressed_string = zlibbed_str[2:-4]
    return base64.b64encode(compressed_string).decode('utf-8').translate(
        str.maketrans('+/', '-_')
    ).rstrip('=')

def convert_puml_to_svg(puml_file, output_dir):
    """Convert a single PlantUML file to SVG"""
    print(f"Converting {puml_file.name}...")
    
    # Read PlantUML content
    with open(puml_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Encode for PlantUML server
    encoded = plantuml_encode(content)
    
    # Use PlantUML server to generate SVG
    url = f"http://www.plantuml.com/plantuml/svg/{encoded}"
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Save SVG file
        output_file = output_dir / f"{puml_file.stem}.svg"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"  ✓ Created {output_file.name}")
        return True
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    # Set paths
    script_dir = Path(__file__).parent
    plantuml_dir = script_dir / "plantuml_sources"
    output_dir = plantuml_dir  # Output SVGs in the same directory
    
    if not plantuml_dir.exists():
        print(f"Error: {plantuml_dir} not found!")
        return
    
    # Find all .puml files
    puml_files = list(plantuml_dir.glob("*.puml"))
    
    if not puml_files:
        print("No .puml files found!")
        return
    
    print(f"Found {len(puml_files)} PlantUML files to convert\n")
    
    # Convert each file
    success_count = 0
    for puml_file in puml_files:
        if convert_puml_to_svg(puml_file, output_dir):
            success_count += 1
    
    print(f"\n{'='*50}")
    print(f"Conversion complete: {success_count}/{len(puml_files)} files converted successfully")
    print(f"{'='*50}")

if __name__ == "__main__":
    main()
