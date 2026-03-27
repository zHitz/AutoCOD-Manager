import re
import os

filepath = 'backend/core/workflow/core_actions.py'
with open(filepath, 'r', encoding='utf-8') as f:
    text = f.read()

old_def_exact = '''def _human_delay(base_sec: float, variance: float = 0.4):
    """Sleep with ±variance randomization to avoid bot-like fixed timing."""
    jitter = base_sec * variance
    delay = base_sec + random.uniform(-jitter, jitter)
    time.sleep(max(0.5, delay))'''

new_def_exact = '''def _human_delay(base_sec: float, variance: float = 0.2):
    """Sleep with Gaussian randomization to simulate human reaction time."""
    sigma = base_sec * variance
    delay = random.gauss(base_sec, sigma)
    time.sleep(max(0.1, delay))'''

if old_def_exact in text:
    print("Found exact _human_delay, replacing...")
    text = text.replace(old_def_exact, new_def_exact)
else:
    print("Could not find exact _human_delay, proceeding with regex...")

# Hide the time.sleep inside _human_delay so it doesn't get swept
text = text.replace("time.sleep(max(0.1, delay))", "TIME_SLEEP_PLACEHOLDER")

# Now change all time.sleep(...) to _human_delay(...)
text = re.sub(r'time\.sleep\(([\d.]+)\)', r'_human_delay(\1)', text)

# Restore the placehoder
text = text.replace("TIME_SLEEP_PLACEHOLDER", "time.sleep(max(0.1, delay))")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(text)

print("Done Refactoring!")
