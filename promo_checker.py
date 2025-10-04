import requests
import re
import time
import os
from typing import Dict, Optional, List
from datetime import datetime

def extract_gift_code(text: str) -> Optional[str]:
    """Extract gift code from URL or return the code if it's already extracted."""
    patterns = [
        r'discord\.gift/([A-Za-z0-9]{16,25})',
        r'discord\.com/gifts/([A-Za-z0-9]{16,25})',
        r'discordapp\.com/gifts/([A-Za-z0-9]{16,25})',
        r'promos\.discord\.gg/([A-Za-z0-9]{16,25})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    if re.match(r'^[A-Za-z0-9]{16,25}$', text.strip()):
        return text.strip()
    
    return None

def check_promo_code(code: str, debug: bool = False, max_retries: int = 3) -> Dict:
    """Check Discord promo/gift code status without claiming it."""
    url = f"https://discord.com/api/v9/entitlements/gift-codes/{code}"
    params = {
        'with_application': 'false',
        'with_subscription_plan': 'true'
    }
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if debug:
                    print(f"\nDEBUG - Raw API Response:")
                    print(f"{data}\n")
                
                is_redeemed = data.get('redeemed', False)
                uses = data.get('uses', 0)
                max_uses = data.get('max_uses', 1)
                
                plan_info = data.get('subscription_plan', {})
                plan_name = plan_info.get('name', 'Unknown')
                
                if is_redeemed or uses >= max_uses:
                    status = "CLAIMED"
                    status_emoji = "❌"
                else:
                    status = "CLAIMABLE"
                    status_emoji = "✅"
                
                extra_info = ""
                if uses > 0 or max_uses > 1:
                    extra_info = f" (Uses: {uses}/{max_uses})"
                
                return {
                    'code': code,
                    'valid': True,
                    'status': status,
                    'emoji': status_emoji,
                    'plan': plan_name,
                    'uses': uses,
                    'max_uses': max_uses,
                    'message': f"{status_emoji} Code is {status} - {plan_name}{extra_info}",
                    'raw_data': data if debug else None
                }
            
            elif response.status_code == 404:
                return {
                    'code': code,
                    'valid': False,
                    'status': 'INVALID',
                    'emoji': '⚠️',
                    'plan': 'N/A',
                    'message': '⚠️ Code is INVALID (Unknown Gift Code)'
                }
            
            elif response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after = int(response.headers.get('Retry-After', 3))
                    wait_time = min(retry_after * (2 ** attempt), 30)
                    if debug:
                        print(f"Rate limited, waiting {wait_time}s before retry {attempt + 1}/{max_retries}...")
                    time.sleep(wait_time)
                    continue
                else:
                    return {
                        'code': code,
                        'valid': False,
                        'status': 'RATE_LIMITED',
                        'emoji': '⏳',
                        'plan': 'N/A',
                        'message': '⏳ Rate limited - Try again later or increase delay'
                    }
            
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('message', 'Unknown error')
                
                return {
                    'code': code,
                    'valid': False,
                    'status': 'ERROR',
                    'emoji': '❌',
                    'plan': 'N/A',
                    'message': f'❌ Error checking code: {error_msg}'
                }
        
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                wait_time = min(2 * (2 ** attempt), 10)
                time.sleep(wait_time)
                continue
            return {
                'code': code,
                'valid': False,
                'status': 'ERROR',
                'emoji': '❌',
                'plan': 'N/A',
                'message': f'❌ Network error: {str(e)}'
            }
    
    return {
        'code': code,
        'valid': False,
        'status': 'ERROR',
        'emoji': '❌',
        'plan': 'N/A',
        'message': f'❌ Max retries exceeded'
    }

def bulk_check_from_file(filename: str, output_file: str = None, delay: float = 2.5):
    """Check multiple promo codes from a text file."""
    
    if not os.path.exists(filename):
        print(f"❌ Error: File '{filename}' not found!")
        return
    
    with open(filename, 'r') as f:
        lines = f.readlines()
    
    codes_to_check = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            code = extract_gift_code(line)
            if code:
                codes_to_check.append(code)
    
    if not codes_to_check:
        print("❌ No valid codes found in the file!")
        return
    
    print(f"\n{'=' * 70}")
    print(f"Bulk Promo Code Check - Found {len(codes_to_check)} codes")
    print(f"{'=' * 70}\n")
    
    results = {
        'claimable': [],
        'claimed': [],
        'invalid': [],
        'rate_limited': [],
        'error': []
    }
    
    for i, code in enumerate(codes_to_check, 1):
        print(f"[{i}/{len(codes_to_check)}] Checking: {code}...", end=" ")
        
        result = check_promo_code(code)
        
        if result['status'] == 'CLAIMABLE':
            results['claimable'].append(result)
            print(f"✅ CLAIMABLE - {result['plan']}")
        elif result['status'] == 'CLAIMED':
            results['claimed'].append(result)
            print(f"❌ CLAIMED - {result['plan']}")
        elif result['status'] == 'INVALID':
            results['invalid'].append(result)
            print(f"⚠️ INVALID")
        elif result['status'] == 'RATE_LIMITED':
            results['rate_limited'].append(result)
            print(f"⏳ RATE LIMITED")
        else:
            results['error'].append(result)
            print(f"❌ ERROR")
        
        if i < len(codes_to_check):
            time.sleep(delay)
    
    print(f"\n{'=' * 70}")
    print("Summary:")
    print(f"{'=' * 70}")
    print(f"✅ Claimable: {len(results['claimable'])}")
    print(f"❌ Claimed: {len(results['claimed'])}")
    print(f"⚠️ Invalid: {len(results['invalid'])}")
    print(f"⏳ Rate Limited: {len(results['rate_limited'])}")
    print(f"❌ Errors: {len(results['error'])}")
    print(f"{'=' * 70}\n")
    
    if results['rate_limited']:
        print("💡 TIP: Increase delay between checks to avoid rate limiting.\n")
    
    if output_file:
        save_results(results, output_file)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_output = f"results_{timestamp}.txt"
        save_results(results, default_output)

def save_results(results: Dict, filename: str):
    """Save checking results to a file."""
    with open(filename, 'w') as f:
        f.write("=" * 70 + "\n")
        f.write(f"Discord Promo Code Check Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 70 + "\n\n")
        
        if results['claimable']:
            f.write(f"✅ CLAIMABLE CODES ({len(results['claimable'])}):\n")
            f.write("-" * 70 + "\n")
            for r in results['claimable']:
                f.write(f"Code: {r['code']}\n")
                f.write(f"Plan: {r['plan']}\n")
                f.write(f"Status: {r['message']}\n")
                f.write("-" * 70 + "\n")
            f.write("\n")
        
        if results['claimed']:
            f.write(f"❌ CLAIMED CODES ({len(results['claimed'])}):\n")
            f.write("-" * 70 + "\n")
            for r in results['claimed']:
                f.write(f"Code: {r['code']}\n")
                f.write(f"Plan: {r['plan']}\n")
                f.write("-" * 70 + "\n")
            f.write("\n")
        
        if results['invalid']:
            f.write(f"⚠️ INVALID CODES ({len(results['invalid'])}):\n")
            f.write("-" * 70 + "\n")
            for r in results['invalid']:
                f.write(f"Code: {r['code']}\n")
                f.write("-" * 70 + "\n")
            f.write("\n")
        
        if results.get('rate_limited'):
            f.write(f"⏳ RATE LIMITED CODES ({len(results['rate_limited'])}):\n")
            f.write("-" * 70 + "\n")
            for r in results['rate_limited']:
                f.write(f"Code: {r['code']}\n")
                f.write(f"Message: {r['message']}\n")
                f.write("-" * 70 + "\n")
            f.write("\n")
            f.write("💡 TIP: Re-run these codes with a higher delay (3-5 seconds)\n")
            f.write("to avoid Discord's rate limits.\n\n")
        
        if results['error']:
            f.write(f"❌ ERROR CODES ({len(results['error'])}):\n")
            f.write("-" * 70 + "\n")
            for r in results['error']:
                f.write(f"Code: {r['code']}\n")
                f.write(f"Message: {r['message']}\n")
                f.write("-" * 70 + "\n")
    
    print(f"💾 Results saved to: {filename}\n")

def interactive_mode():
    """Run the checker in interactive mode."""
    print("This tool checks Discord promo/gift codes WITHOUT claiming them.")
    print("Type 'debug' to enable debug mode, 'quit' to exit.\n")
    print("NOTE: Discord's API may not always accurately report claimed")
    print("status. If you see a code as 'CLAIMABLE' but it's claimed,")
    print("enable debug mode to see the raw API response.\n")
    
    debug_mode = False
    
    while True:
        user_input = input("Enter promo code or URL (or 'quit'): ").strip()
        
        if user_input.lower() in ['quit', 'exit', 'q']:
            print("\nExiting... Goodbye!")
            break
        
        if user_input.lower() == 'debug':
            debug_mode = not debug_mode
            status = "enabled" if debug_mode else "disabled"
            print(f"🔧 Debug mode {status}\n")
            continue
        
        if not user_input:
            continue
        
        code = extract_gift_code(user_input)
        
        if not code:
            print("⚠️ Invalid format. Please enter a valid Discord promo code or gift URL.\n")
            continue
        
        print(f"\nChecking code: {code}")
        print("-" * 60)
        
        result = check_promo_code(code, debug=debug_mode)
        
        print(f"Code: {result['code']}")
        print(f"Status: {result['message']}")
        
        if result['valid'] and result['plan']:
            print(f"Plan: {result['plan']}")
        
        print("-" * 60 + "\n")
        
        time.sleep(0.5)

def main():
    """Main function to run the promo code checker."""
    print("=" * 70)
    print("Discord Promo Code Checker")
    print("=" * 70)
    print("\nChoose a mode:")
    print("1. Interactive Mode - Check codes one by one")
    print("2. Bulk Mode - Check codes from a text file")
    print()
    
    choice = input("Enter your choice (1 or 2): ").strip()
    
    if choice == '1':
        print("\n" + "=" * 70)
        print("Interactive Mode")
        print("=" * 70 + "\n")
        interactive_mode()
    elif choice == '2':
        print("\n" + "=" * 70)
        print("Bulk Mode")
        print("=" * 70 + "\n")
        filename = input("Enter the filename with codes (e.g., codes.txt): ").strip()
        
        print("\n💡 Recommended delay: 2-3 seconds to avoid rate limiting")
        delay_input = input("Delay between checks in seconds (default 2.5): ").strip()
        delay = 2.5
        if delay_input:
            try:
                delay = float(delay_input)
                if delay < 0:
                    print(f"⚠️ Delay cannot be negative, using default: 2.5 seconds")
                    delay = 2.5
                elif delay > 60:
                    print(f"⚠️ Delay too large (max 60s), using 60 seconds")
                    delay = 60.0
            except ValueError:
                print(f"⚠️ Invalid delay value, using default: 2.5 seconds")
                delay = 2.5
        
        bulk_check_from_file(filename, delay=delay)
    else:
        print("Invalid choice. Exiting...")

if __name__ == "__main__":
    main()
