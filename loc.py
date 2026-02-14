import os

def count_loc():
    # Metrics containers
    total_all = 0
    total_commented = 0
    total_empty = 0
    total_logic = 0  # No empty, no comments
    
    # Get all .py files in current directory, excluding this script
    files = [f for f in os.listdir('.') if f.endswith('.py') and f != 'loc.py' and os.path.isfile(f)]
    
    header = f"{'File':<20} | {'Total':<6} | {'Comm':<6} | {'-Comm':<6} | {'-Empty':<7} | {'Logic':<6}"
    print(header)
    print("-" * len(header))
    
    for filename in sorted(files):
        with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            
        f_total = len(lines)
        f_commented = 0
        f_empty = 0
        f_logic = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                f_empty += 1
            elif stripped.startswith('#'):
                f_commented += 1
            else:
                f_logic += 1
        
        # Calculate derived metrics
        f_without_comm = f_total - f_commented
        f_without_empty = f_total - f_empty
        
        print(f"{filename:<20} | {f_total:<6} | {f_commented:<6} | {f_without_comm:<6} | {f_without_empty:<7} | {f_logic:<6}")
        
        total_all += f_total
        total_commented += f_commented
        total_empty += f_empty
        total_logic += f_logic

    print("-" * len(header))
    print(f"{'TOTAL':<20} | {total_all:<6} | {total_commented:<6} | {total_all - total_commented:<6} | {total_all - total_empty:<7} | {total_logic:<6}")

if __name__ == '__main__':
    count_loc()
