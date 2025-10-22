#!/usr/bin/env python3
import subprocess, json, sys, os
import tkinter as tk
import threading

try:
    layout = json.load(open(sys.argv[1]))
except FileNotFoundError:
    print(f"Error: JSON file not found at {sys.argv[1]}", file=sys.stderr)
    sys.exit(1)
except json.JSONDecodeError as e:
    print(f"Error: JSON Decode Error: {e}", file=sys.stderr)
    sys.exit(1)
except IndexError: # Specific error for missing sys.argv[1]
    print('Error: No layout file supplied.', file=sys.stderr)
    print(f'Usage: {sys.argv[0]} <layout.json>', file=sys.stderr)
    sys.exit(1)
except Exception as e: # Catch other potential startup errors
    print(f"An unexpected error occurred: {e}", file=sys.stderr)
    sys.exit(1)

buttons = {}

class Application(tk.Frame):
    def __init__(self, master=None):
        tk.Frame.__init__(self, master,
                          width=layout['width'],
                          height=layout['height'])
        
        self['bg'] = layout['rootbg']
        self.pack()
        self.create_widgets()
        
        self.proc = None # Will store the subprocess instance
        
        # Start the xinput listener in a separate thread
        self.start_xinput_listener()
        
        # Add a handler for the window's close button
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        """Creates the labels based on the layout file."""
        for button in layout['buttons']:
            btn = tk.Label(self, text=button['text']) 
            btn.place(width=button['width'], height=button['height'],
                      x=button['x'], y=button['y'])
            btn['bg'] = layout['bg1']
            btn['fg'] = layout['fg1']
            btn['font'] = (layout['fontfamily'], layout['fontsize'], layout['fontweight'])

            buttons[button['keycode']] = btn

    def start_xinput_listener(self):
        """Creates and starts a daemon thread to run the _xinput_loop."""
        # will exit automatically when the main program exits
        self.listener_thread = threading.Thread(target=self._xinput_loop, daemon=True)
        self.listener_thread.start()

    def _xinput_loop(self):
        try:
            self.proc = subprocess.Popen(['xinput', 'test-xi2', '--root'],
                                         stdout=subprocess.PIPE,
                                         stderr=subprocess.PIPE,
                                         bufsize=1, # Line buffered
                                         universal_newlines=True) 
        except FileNotFoundError:
            print("Error: 'xinput' command not found. This program requires 'xinput'.", file=sys.stderr)
            # Schedule the application to quit from the main thread
            self.master.after(0, self.master.quit)
            return
        except Exception as e:
            print(f"Error starting subprocess: {e}", file=sys.stderr)
            self.master.after(0, self.master.quit)
            return

        inkeypressevent = False
        inkeyrelevent = False

        # Will loop until the process ends
        for line in iter(self.proc.stdout.readline, ''):
            if 'EVENT type 2 (KeyPress)' in line:
                inkeypressevent = True
                inkeyrelevent = False 
            elif 'EVENT type 3 (KeyRelease)' in line:
                inkeyrelevent = True
                inkeypressevent = False
            elif 'detail:' in line.strip():
                if inkeypressevent or inkeyrelevent:
                    try:
                        code = int(line.split()[1])
                        if inkeypressevent:
                            self.master.after(0, self.update_button, code, layout['bg2'])
                            self.master.after(0, self.update_button, code, layout['fg2'])
                        elif inkeyrelevent:
                            self.master.after(0, self.update_button, code, layout['bg1'])
                    except (ValueError, IndexError):
                        pass # Ignore malformed lines
                    
                    # Reset flags
                    inkeypressevent = False
                    inkeyrelevent = False
        
        self.proc.stdout.close()
        self.proc.stderr.close()
        self.proc.wait()

    def update_button(self, keycode, color):
        try:
            buttons[keycode]['bg'] = color
        except KeyError:
            pass # No button assigned to this keycode, which is fine

    def on_closing(self):
        print("Closing application...")
        if self.proc:
            # Terminate the subprocess
            self.proc.terminate()
            try:
                # Give it a moment to die
                self.proc.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                self.proc.kill() # Force kill if it doesn't terminate
                
        # Destroy the Tkinter window, which stops the mainloop
        self.master.destroy()

# --- Main execution ---
if __name__ == "__main__":
    root = tk.Tk()
    root.title("kbdisplay")
    app = Application(master=root)
    app.mainloop()
