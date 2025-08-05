import re
import sys

def clean_perusall_file(input_path, output_path=None):
    """Clean Perusall export and extract readable text."""
    
    try:
        # Read the input file
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract text using regex
        pattern = r"'str':\s*'([^']*)'"
        matches = re.findall(pattern, content)
        
        # Filter out empty/meaningless text
        clean_text_pieces = []
        for match in matches:
            text = match.strip()
            if text and len(text) > 0 and text not in [' ', '', '\n', '\t']:
                clean_text_pieces.append(text)
        
        # Join text and clean spacing
        result = ' '.join(clean_text_pieces)
        result = re.sub(r'\s+', ' ', result).strip()
        
        # Add paragraph breaks for readability
        result = re.sub(r'\. ([A-Z])', r'.\n\n\1', result)
        
        # Save or return result
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(result)
            print(f"✅ Text cleaned and saved to: {output_path}")
            print(f"📊 Original file: {len(content):,} characters")
            print(f"📊 Cleaned text: {len(result):,} characters")
            print(f"📊 Extracted {len(clean_text_pieces)} text segments")
        else:
            return result
            
    except FileNotFoundError:
        print(f"❌ Error: File '{input_path}' not found")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    if len(sys.argv) < 2:
        print("Usage: python clean_text.py input_file.txt [output_file.txt]")
        print("Example: python clean_text.py paste.txt cleaned_output.txt")
        return
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else input_file.replace('.txt', '_cleaned.txt')
    
    clean_perusall_file(input_file, output_file)

if __name__ == "__main__":
    main()