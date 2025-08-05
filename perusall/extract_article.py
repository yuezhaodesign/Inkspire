#!/usr/bin/env python3
"""
Complete Perusall Text Extractor - All-in-One Script
Save this as: extract_article.py
"""

import json
import requests
from typing import Dict, Any
import time
from datetime import datetime, timezone
import os
import glob

class DirectPerusallExtractor:
    def __init__(self, delay_seconds: float = 1.0):
        """
        Initialize the extractor
        
        Args:
            delay_seconds: Delay between API requests to be respectful
        """
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        # Add realistic headers
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
    
    def load_json_file(self, file_path: str) -> Dict[str, Any]:
        """Load and validate the Perusall JSON file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            
            # Handle case where file might not start with { (incomplete JSON)
            if not content.startswith('{'):
                # Try to find the start of JSON
                json_start = content.find('{')
                if json_start != -1:
                    content = content[json_start:]
                else:
                    raise ValueError("No valid JSON found in file")
            
            # Handle case where file might not end with } (incomplete JSON)
            if not content.endswith('}') and not content.endswith(']'):
                # Try to find the last valid JSON ending
                for ending in ['}', ']']:
                    last_pos = content.rfind(ending)
                    if last_pos != -1:
                        content = content[:last_pos + 1]
                        break
            
            data = json.loads(content)
            
            # Validate that we have the expected structure
            if not isinstance(data, dict):
                raise ValueError("JSON must be a dictionary/object")
            
            if 'pages' not in data:
                raise ValueError("JSON must contain a 'pages' array")
            
            if not isinstance(data['pages'], list):
                raise ValueError("'pages' must be an array")
            
            if len(data['pages']) == 0:
                raise ValueError("'pages' array is empty")
            
            return data
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON format: {e}")
    
    def is_url_expired(self, expires_at: str) -> bool:
        """Check if URL has expired"""
        try:
            if expires_at.endswith('Z'):
                expire_time = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
            else:
                expire_time = datetime.fromisoformat(expires_at)
            
            if expire_time.tzinfo is None:
                expire_time = expire_time.replace(tzinfo=timezone.utc)
            
            current_time = datetime.now(timezone.utc)
            return current_time > expire_time
            
        except (ValueError, TypeError):
            return False  # Assume not expired if we can't parse
    
    def extract_text_from_response(self, response_data: Dict[str, Any]) -> str:
        """Extract text from various possible response formats"""
        text_content = ""
        
        # Method 1: Direct text field
        if 'text' in response_data:
            if isinstance(response_data['text'], str):
                text_content = response_data['text']
            elif isinstance(response_data['text'], list):
                text_parts = []
                for item in response_data['text']:
                    if isinstance(item, str):
                        text_parts.append(item)
                    elif isinstance(item, dict):
                        # Look for text in common fields
                        for field in ['content', 'text', 'value', 'data']:
                            if field in item:
                                text_parts.append(str(item[field]))
                                break
                    else:
                        text_parts.append(str(item))
                text_content = ' '.join(text_parts)
        
        # Method 2: Content field
        elif 'content' in response_data:
            text_content = str(response_data['content'])
        
        # Method 3: Data field with text items
        elif 'data' in response_data:
            data = response_data['data']
            if isinstance(data, list):
                text_parts = []
                for item in data:
                    if isinstance(item, dict):
                        # Look for text in the item
                        for field in ['text', 'content', 'value']:
                            if field in item:
                                text_parts.append(str(item[field]))
                                break
                    else:
                        text_parts.append(str(item))
                text_content = ' '.join(text_parts)
            else:
                text_content = str(data)
        
        # Method 4: Look for any field that might contain text
        else:
            possible_fields = ['textContent', 'body', 'html', 'plain', 'raw', 'items']
            for field in possible_fields:
                if field in response_data:
                    if isinstance(response_data[field], list):
                        text_content = ' '.join(str(item) for item in response_data[field])
                    else:
                        text_content = str(response_data[field])
                    break
        
        return text_content.strip()
    
    def fetch_page_text(self, url: str, page_number: int) -> str:
        """Fetch text content for a single page"""
        try:
            print(f"    Requesting: {url[:100]}...")
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Try to parse as JSON
            try:
                data = response.json()
                text = self.extract_text_from_response(data)
                
                if text:
                    print(f"    ✓ Extracted {len(text)} characters")
                    return text
                else:
                    print(f"    ⚠ No text found in response")
                    print(f"    Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                    return ""
                    
            except json.JSONDecodeError:
                # If not JSON, treat as plain text
                text = response.text.strip()
                if text:
                    print(f"    ✓ Got plain text: {len(text)} characters")
                    return text
                else:
                    print(f"    ⚠ Empty response")
                    return ""
            
        except requests.exceptions.Timeout:
            print(f"    ✗ Timeout after 30 seconds")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"    ✗ Request failed: {e}")
            return ""
        except Exception as e:
            print(f"    ✗ Unexpected error: {e}")
            return ""
    
    def extract_document(self, json_file_path: str, output_file: str = None) -> str:
        """Extract text from the entire document"""
        
        print(f"Loading Perusall JSON: {json_file_path}")
        data = self.load_json_file(json_file_path)
        
        doc_name = data.get('name', 'Unknown Document')
        doc_id = data.get('_id', 'unknown')
        pages = data['pages']
        
        print(f"Document: {doc_name}")
        print(f"ID: {doc_id}")
        print(f"Pages: {len(pages)}")
        print("=" * 60)
        
        extracted_pages = []
        successful = 0
        failed = 0
        expired = 0
        
        for i, page in enumerate(pages, 1):
            page_num = page.get('number', i)
            print(f"\nPage {page_num} ({i}/{len(pages)}):")
            
            if 'textContentUrl' not in page:
                print(f"    ✗ No textContentUrl found")
                failed += 1
                continue
            
            # Check expiration
            if 'expiresAt' in page and self.is_url_expired(page['expiresAt']):
                print(f"    ✗ URL expired at {page['expiresAt']}")
                expired += 1
                continue
            
            # Fetch the text
            text = self.fetch_page_text(page['textContentUrl'], page_num)
            
            if text:
                extracted_pages.append(f"=== PAGE {page_num} ===\n\n{text}")
                successful += 1
            else:
                failed += 1
            
            # Be respectful with delays
            if i < len(pages):
                time.sleep(self.delay_seconds)
        
        print("\n" + "=" * 60)
        print("EXTRACTION SUMMARY:")
        print(f"  ✓ Successful: {successful}")
        print(f"  ✗ Failed: {failed}")
        print(f"  ⏰ Expired: {expired}")
        print(f"  📄 Total pages: {len(pages)}")
        
        if not extracted_pages:
            raise ValueError("No pages could be extracted. Check if URLs have expired or are accessible.")
        
        # Combine all pages
        full_text = f"DOCUMENT: {doc_name}\nSOURCE: Perusall Export\nEXTRACTED: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n" + "\n\n".join(extracted_pages)
        
        # Save if requested
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(full_text)
            print(f"\n💾 Saved to: {output_file}")
        
        return full_text

def find_json_files():
    """Find all JSON files in the current directory"""
    json_files = glob.glob("*.json")
    return json_files

def main():
    """Main extraction function"""
    print("🔍 Perusall Text Extractor")
    print("=" * 40)
    
    # Look for JSON files
    json_files = find_json_files()
    
    if not json_files:
        print("❌ No JSON files found in current directory.")
        print("\n💡 Please:")
        print("   1. Make sure your Perusall JSON file is in this folder")
        print("   2. Make sure it has a .json extension")
        print("   3. Common names: perusall_data.json, document.json, etc.")
        return
    
    # If only one JSON file, use it
    if len(json_files) == 1:
        json_file = json_files[0]
        print(f"📄 Found JSON file: {json_file}")
    else:
        # Let user choose
        print(f"📄 Found {len(json_files)} JSON files:")
        for i, file in enumerate(json_files, 1):
            print(f"   {i}. {file}")
        
        while True:
            try:
                choice = input(f"\nSelect file (1-{len(json_files)}): ").strip()
                idx = int(choice) - 1
                if 0 <= idx < len(json_files):
                    json_file = json_files[idx]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(json_files)}")
            except ValueError:
                print("Please enter a valid number")
    
    # Generate output filename
    base_name = os.path.splitext(json_file)[0]
    output_file = f"{base_name}_extracted.txt"
    
    print(f"\n🚀 Starting extraction...")
    print(f"📥 Input:  {json_file}")
    print(f"📤 Output: {output_file}")
    print("-" * 40)
    
    try:
        # Extract the text
        extractor = DirectPerusallExtractor(delay_seconds=0.8)
        text = extractor.extract_document(json_file, output_file)
        
        print(f"\n🎉 EXTRACTION COMPLETE!")
        print(f"📊 Characters: {len(text):,}")
        print(f"📊 Words: {len(text.split()):,}")
        print(f"📁 Saved to: {output_file}")
        
        # Show a preview
        print(f"\n📖 PREVIEW:")
        print("=" * 50)
        lines = text.split('\n')[:15]  # First 15 lines
        for line in lines:
            print(line[:100] + ("..." if len(line) > 100 else ""))
        
        if len(text.split('\n')) > 15:
            print(f"... (and {len(text.split('\n')) - 15} more lines)")
        
        print("\n✅ Done! You can now open the .txt file to read the content.")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        
        # Provide helpful troubleshooting
        print(f"\n🔧 Troubleshooting:")
        print(f"   • Make sure '{json_file}' is a valid Perusall JSON export")
        print(f"   • Check your internet connection")
        print(f"   • The URLs in the JSON file might have expired")
        print(f"   • Try re-exporting from Perusall if URLs are old")

if __name__ == "__main__":
    main()