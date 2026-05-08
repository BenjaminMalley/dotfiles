import sys
import os

def send_notification(message="The command has finished.", title="Gemini"):
    """
    Sends a desktop notification using the OSC 777 sequence.
    This implementation assumes terminal support and handles tmux passthrough.
    Writes to stderr to avoid corrupting stdout in hook scripts.
    """
    # Escape semicolons as they are delimiters in OSC 777
    safe_title = title.replace(';', ':')
    safe_message = message.replace(';', ':')
    
    # OSC 777 format: \033]777;notify;TITLE;MESSAGE\a
    # \033 is ESC, \a is BEL (\007)
    osc_body = f"777;notify;{safe_title};{safe_message}\a"
    
    if 'TMUX' in os.environ:
        # Wrap for tmux passthrough: \033Ptmux;\033\033]...
        # Every \033 (ESC) in the inner sequence must be doubled.
        # The sequence must end with the tmux terminator \033\\
        sequence = f"\033Ptmux;\033\033]{osc_body}\033\\"
    else:
        sequence = f"\033]{osc_body}"
        
    sys.stderr.write(sequence)
    sys.stderr.flush()

def main():
    """Entry point for the notify CLI script."""
    message = sys.argv[1] if len(sys.argv) > 1 else "The command has finished."
    title = sys.argv[2] if len(sys.argv) > 2 else "Gemini"
    send_notification(message, title)
