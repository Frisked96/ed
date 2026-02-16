import os

def count_loc():
    total_lines = 0
    file_count = 0
    
    # Files to exclude
    exclude_files = {'p.py', 'loc.py'}
    # Patterns to exclude
    exclude_patterns = ['analyze', 'stats']
    
    for root, dirs, files in os.walk('.'):
        # Skip hidden directories like .git
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        
        for file in files:
            if not file.endswith('.py'):
                continue
            
            if file in exclude_files:
                continue
            
            should_exclude = False
            for pattern in exclude_patterns:
                if pattern in file:
                    should_exclude = True
                    break
            if should_exclude:
                continue
                
            file_path = os.path.join(root, file)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    total_lines += len(lines)
                    file_count += 1
                    print(f"{len(lines):>6} lines: {file_path}")
            except Exception as e:
                print(f"Could not read {file_path}: {e}")
                
    print("-" * 30)
    print(f"Total LOC: {total_lines} in {file_count} files.")

if __name__ == "__main__":
    count_loc()
