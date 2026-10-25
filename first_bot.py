import os
import platform
from datetime import datetime

# 1. Target output path on your Desktop
desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
report_file = os.path.join(desktop_path, "automation_test_report.txt")

# 2. Automation task: Collect system diagnostics and write to file
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
report_content = f"""========================================
AUTOMATION TEST RUN SUCCESSFUL
========================================
Executed at : {timestamp}
OS Platform : {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Status      : Active & Verified
========================================
Your Python automation workspace is fully operational!
"""

with open(report_file, "w") as f:
    f.write(report_content)

print("--------------------------------------------------")
print("Automation executed successfully!")
print("Report generated on your Desktop: automation_test_report.txt")
print("--------------------------------------------------")