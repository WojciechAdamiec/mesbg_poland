"""Test script to verify the scatter chart has bigger dots with labels"""
import time
import subprocess
import sys

# Install playwright if not present
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "playwright"], timeout=60)

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.set_viewport_size({"width": 1200, "height": 800})
    
    try:
        # Navigate to the page
        print("Loading page...")
        page.goto("http://127.0.0.1:8050/stats/pickrate_vs_winrate", timeout=30000)
        
        # Wait for the chart to render
        print("Waiting for chart to render...")
        page.wait_for_timeout(3000)
        
        # Take a screenshot
        screenshot_path = "C:\\Czyste Archiwum\\Bitewniaki\\mesbg_poland\\chart_screenshot.png"
        page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to: {screenshot_path}")
        
        # Try to find circles (dots) in the SVG
        circles = page.query_selector_all("circle[r]")
        if circles:
            radii = []
            for circle in circles:
                r = circle.get_attribute("r")
                if r and r != "":
                    radii.append(float(r))
            
            if radii:
                avg_radius = sum(radii) / len(radii)
                max_radius = max(radii)
                print(f"[OK] Found {len(circles)} circles")
                print(f"[INFO] Average radius: {avg_radius:.2f}, Max radius: {max_radius:.2f}")
                
                # Check if radius is reasonably large (> 5)
                if max_radius >= 10:
                    print("[OK] Dots are bigger (r >= 10)")
                else:
                    print(f"[WARNING] Dots might be small (max r = {max_radius})")
            else:
                print("[WARNING] No radii found in circles")
        else:
            print("[INFO] No circle elements found - chart might render differently")
        
        # Check for text labels
        texts = page.query_selector_all("text")
        letter_count = 0
        for text in texts:
            content = text.inner_text().strip()
            if len(content) == 1 and content.isalpha():
                letter_count += 1
        
        if letter_count > 10:
            print(f"[OK] Found {letter_count} single-letter labels on the chart")
        elif letter_count > 0:
            print(f"[WARNING] Found only {letter_count} single-letter labels (expected many more)")
        else:
            print("[WARNING] No single-letter labels found on chart")
            
    except Exception as e:
        print(f"[ERROR] {e}")
    finally:
        browser.close()
        print("Browser closed")
