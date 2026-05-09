import sys
import subprocess
import platform

def send_notification(message="The command has finished.", title="Gemini"):
    """
    Sends a desktop notification.
    On macOS, it uses osascript. On other systems, it prints to stdout with a bell.
    """
    system = platform.system()

    if system == 'Darwin':
        # Escape double quotes for AppleScript
        safe_message = message.replace('"', '\\"')
        safe_title = title.replace('"', '\\"')
        
        script = f'display notification "{safe_message}" with title "{safe_title}" sound name "Glass"'
        try:
            subprocess.run(['osascript', '-e', script], check=True)
        except subprocess.CalledProcessError as e:
            sys.stderr.write(f"Error sending notification: {e}\n")
    else:
        # Fallback for other systems
        sys.stdout.write('\a')
        print(f"Notification: {title} - {message}")

def main():
    """Entry point for the notify CLI script."""
    message = sys.argv[1] if len(sys.argv) > 1 else "The command has finished."
    title = sys.argv[2] if len(sys.argv) > 2 else "Gemini"
    send_notification(message, title)

