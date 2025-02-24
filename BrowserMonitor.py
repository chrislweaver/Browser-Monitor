import time
import pygetwindow as gw
import mss
import tkinter as tk
from tkinter import messagebox, Toplevel
from PIL import Image, ImageChops, ImageStat, ImageDraw, ImageTk
import pygame
import threading
import json
import os
import requests
from datetime import datetime

# Initialize pygame mixer
pygame.mixer.init()

# Global variables
selected_window = None
monitoring = False  # Variable to track if monitoring is active
last_screenshot = None  # Holds the last screenshot for comparison

def load_telegram_config():
    """Load Telegram configuration from a JSON file."""
    try:
        with open('telegram_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def setup_telegram_config():
    """Create a window to setup Telegram configuration."""
    config_window = Toplevel()
    config_window.title("Telegram Configuration")
    config_window.geometry("500x450")

    # Create main frame with padding
    main_frame = tk.Frame(config_window, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Instructions
    instructions = """
    To configure Telegram notifications:
    1. Find @BotFather in Telegram
    2. Send /newbot and follow instructions
    3. Save the bot token provided
    4. Send a message to your bot
    5. Find your chat ID using @RawDataBot
    """
    tk.Label(main_frame, text=instructions, justify=tk.LEFT, wraplength=450).pack(pady=(0,20))

    # Bot Token section
    tk.Label(main_frame, text="Bot Token:", anchor='w').pack(fill='x')

    token_frame = tk.Frame(main_frame)
    token_frame.pack(fill='x', pady=(0,10))

    token_entry = tk.Entry(token_frame, width=45, show="●")
    token_entry.pack(side=tk.LEFT)

    def toggle_token():
        if token_entry.cget('show') == "●":
            token_entry.config(show="")
            token_button.config(text="Hide")
        else:
            token_entry.config(show="●")
            token_button.config(text="Show")

    token_button = tk.Button(token_frame, text="Show", command=toggle_token,
                            bg="#6c757d", fg="white", relief="flat", padx=10)
    token_button.pack(side=tk.LEFT, padx=5)

    # Chat ID section
    tk.Label(main_frame, text="Chat ID:", anchor='w').pack(fill='x')

    chat_frame = tk.Frame(main_frame)
    chat_frame.pack(fill='x', pady=(0,20))

    chat_entry = tk.Entry(chat_frame, width=45, show="●")
    chat_entry.pack(side=tk.LEFT)

    def toggle_chat():
        if chat_entry.cget('show') == "●":
            chat_entry.config(show="")
            chat_button.config(text="Hide")
        else:
            chat_entry.config(show="●")
            chat_button.config(text="Show")

    chat_button = tk.Button(chat_frame, text="Show", command=toggle_chat,
                           bg="#6c757d", fg="white", relief="flat", padx=10)
    chat_button.pack(side=tk.LEFT, padx=5)

    # Load existing config if any
    config = load_telegram_config()
    if config:
        token_entry.delete(0, tk.END)  # Clear any existing text
        chat_entry.delete(0, tk.END)   # Clear any existing text
        token_entry.insert(0, config.get('bot_token', ''))
        chat_entry.insert(0, config.get('chat_id', ''))

    def save_config():
        config = {
            'bot_token': token_entry.get().strip(),
            'chat_id': chat_entry.get().strip()
        }

        # Validate inputs
        if not config['bot_token'] or not config['chat_id']:
            messagebox.showerror("Error", "Both Bot Token and Chat ID are required!")
            return

        try:
            with open('telegram_config.json', 'w') as f:
                json.dump(config, f)
            config_window.destroy()
            messagebox.showinfo("Success", "Telegram configuration saved!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save configuration: {str(e)}")

    # Buttons frame
    button_frame = tk.Frame(main_frame)
    button_frame.pack(pady=20)

    tk.Button(button_frame, text="Save Configuration", 
              command=save_config,
              bg="#28a745", fg="white",
              font=("Arial", 10),
              relief="flat", cursor="hand2",
              padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    tk.Button(button_frame, text="Cancel",
              command=config_window.destroy,
              bg="#dc3545", fg="white",
              font=("Arial", 10),
              relief="flat", cursor="hand2",
              padx=20, pady=5).pack(side=tk.LEFT, padx=5)

def view_telegram_config():
    """Display current Telegram configuration."""
    config = load_telegram_config()
    if not config:
        messagebox.showinfo("Configuration", "No Telegram configuration found!")
        return

    config_window = Toplevel()
    config_window.title("Current Telegram Configuration")
    config_window.geometry("400x300")

    frame = tk.Frame(config_window, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    tk.Label(frame, text="Current Telegram Configuration", 
             font=("Arial", 12, "bold")).pack(pady=(0,20))

    # Create status display
    status_frame = tk.Frame(frame)
    status_frame.pack(fill='x', pady=5)

    # Show status indicators, not actual values
    tk.Label(status_frame, text="Bot Token:", font=("Arial", 10, "bold")).pack(anchor='w')
    tk.Label(status_frame, text="[Configured]", fg="green").pack(anchor='w', padx=20)

    tk.Label(status_frame, text="Chat ID:", font=("Arial", 10, "bold")).pack(anchor='w', pady=(10,0))
    tk.Label(status_frame, text="[Configured]", fg="green").pack(anchor='w', padx=20)

    def remove_configuration():
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the current configuration?"):
            try:
                if os.path.exists('telegram_config.json'):
                    os.remove('telegram_config.json')
                messagebox.showinfo("Success", "Configuration removed successfully!")
                config_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove configuration: {str(e)}")

    # Add some space before buttons
    tk.Frame(frame, height=20).pack()

    # Button frame
    button_frame = tk.Frame(frame)
    button_frame.pack(pady=10)

    # Remove Configuration button
    tk.Button(button_frame, 
              text="Remove Configuration",
              command=remove_configuration,
              bg="#dc3545", 
              fg="white",
              font=("Arial", 10),
              relief="flat", 
              cursor="hand2",
              padx=20, 
              pady=5).pack(pady=10)

    # Close button
    tk.Button(button_frame, 
              text="Close",
              command=config_window.destroy,
              bg="#6c757d", 
              fg="white",
              font=("Arial", 10),
              relief="flat", 
              cursor="hand2",
              padx=20, 
              pady=5).pack(pady=10)
                  
def send_telegram_notification(overlay_image=None):
    """Send Telegram notification with screenshot when changes are detected."""
    config = load_telegram_config()
    if not config:
        messagebox.showerror("Error", "Telegram configuration not found!")
        return

    bot_token = config['bot_token']
    chat_id = config['chat_id']
    base_url = f"https://api.telegram.org/bot{bot_token}"

    try:
        # Get current time
        current_time = datetime.now().strftime("%I:%M:%S %p")

        # Send text message with timestamp
        message_text = f"🔔 Change detected in monitored browser window!\n⏰ Time: {current_time}"
        response = requests.post(
            f"{base_url}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message_text,
                "parse_mode": "HTML"
            }
        )

        # If we have an image, send it
        if overlay_image:
            # Save the image temporarily
            temp_image_path = "temp_screenshot.png"
            overlay_image.save(temp_image_path)

            # Send the image
            with open(temp_image_path, 'rb') as image_file:
                response = requests.post(
                    f"{base_url}/sendPhoto",
                    data={
                        "chat_id": chat_id,
                        "caption": "Screenshot showing detected changes (highlighted in red)"
                    },
                    files={
                        "photo": image_file
                    }
                )

            # Clean up temporary file
            try:
                os.remove(temp_image_path)
            except:
                pass

        print("Telegram notification sent successfully!")
    except Exception as e:
        print(f"Error sending Telegram notification: {e}")
        messagebox.showerror("Error", f"Failed to send Telegram notification: {str(e)}")

def test_telegram_configuration():
    """Test Telegram configuration by sending a test message."""
    config = load_telegram_config()
    if not config:
        messagebox.showerror("Error", "Telegram configuration not found!\nPlease set up Telegram configuration first.")
        return

    try:
        bot_token = config['bot_token']
        chat_id = config['chat_id']
        message = """
🔧 Test message from Browser Monitor

If you receive this message, your Telegram configuration is working correctly!

Configuration details:
• Bot connected successfully
• Messages can be sent to your chat
• Ready to send notifications
        """

        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
        )

        if response.status_code == 200:
            messagebox.showinfo("Success", "Test message sent successfully!\nPlease check your Telegram for the message.")
        else:
            messagebox.showerror("Error", f"Failed to send test message.\nStatus code: {response.status_code}")

    except Exception as e:
        messagebox.showerror("Error", f"Failed to send test message: {str(e)}\n\nPlease verify your bot token and chat ID.")

def play_sound():
    """Play a notification sound."""
    try:
        pygame.mixer.music.load("notification.mp3")
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error with pygame.mixer: {e}")
        try:
            os.system("start notification.mp3")
        except Exception as e:
            print(f"Error with os.system sound: {e}")

def list_browser_windows():
    """List browser windows available for monitoring."""
    windows = gw.getWindowsWithTitle("")
    browser_windows = [
        win for win in windows if win.title and any(browser in win.title for browser in ["Chrome", "Firefox", "Brave", "Vivaldi"])
    ]
    return browser_windows

def select_window():
    """Open a dialog to allow the user to select a browser window."""
    global selected_window, selected_window_label
    windows = list_browser_windows()

    if not windows:
        messagebox.showerror("Error", "No browser windows found!")
        return

    selection_window = tk.Toplevel(root)
    selection_window.title("Select Window")
    selection_window.geometry("500x300")

    button_frame = tk.Frame(selection_window)
    button_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for win in windows:
        btn = tk.Button(button_frame, text=win.title, anchor="w", 
                       command=lambda w=win: set_selected_window(w, selection_window))
        btn.pack(fill=tk.X, padx=5, pady=2, ipadx=5)

def set_selected_window(window, selection_window):
    """Set the selected window for monitoring."""
    global selected_window
    selected_window = window
    update_status_indicator(False)
    selected_window_label.config(
        text=f"Selected Browser Window:\n{selected_window.title}",
        bg="#f1f1f1",
        relief="solid",
        bd=1,
        fg="black",
    )
    selection_window.destroy()
def capture_window(window):
    """Capture a screenshot of the selected window."""
    if not window:
        return None
    try:
        # Add error checking for window state
        if not window.isMinimized:
            window.activate()
            time.sleep(0.5)  # Reduced sleep time

            # Ensure coordinates are positive
            left = max(0, window.left)
            top = max(0, window.top)
            width = window.width
            height = window.height

            # Capture screenshot of the selected window
            with mss.mss() as sct:
                monitor = {"left": left, "top": top, "width": width, "height": height}
                try:
                    screenshot = sct.grab(monitor)
                    img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                    return img
                except Exception as e:
                    print(f"Screenshot capture error: {e}")
                    return None
    except Exception as e:
        print(f"Window activation error: {e}")
        # Fallback capture attempt
        try:
            with mss.mss() as sct:
                monitor = {"left": window.left, "top": window.top, 
                          "width": window.width, "height": window.height}
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                return img
        except Exception as e:
            print(f"Fallback capture error: {e}")
            return None
    return None

def divide_image_into_tiles(image, tile_size):
    """Divide the screenshot into smaller tiles (regions) for more granular comparison."""
    tiles = []
    width, height = image.size
    for y in range(0, height, tile_size):
        for x in range(0, width, tile_size):
            box = (x, y, min(x + tile_size, width), min(y + tile_size, height))
            tiles.append((box, image.crop(box)))
    return tiles

def calculate_image_difference(img1, img2):
    """Calculate the visual difference between two images."""
    try:
        diff = ImageChops.difference(img1, img2)
        stat = ImageStat.Stat(diff)
        diff_mean = sum(stat.mean) / len(stat.mean)  # Average difference in pixel values
        return diff_mean
    except Exception as e:
        print(f"Error calculating image difference: {e}")
        return 0

def monitor_window():
    """Continuously monitor the selected window for visual changes."""
    global monitoring, last_screenshot

    if not selected_window:
        messagebox.showerror("Error", "No window selected!")
        return

    # Capture the initial screenshot for comparison
    last_screenshot = capture_window(selected_window)

    if last_screenshot is None:
        messagebox.showerror("Error", "Could not capture the selected window.")
        return

    while monitoring:
        time.sleep(1)  # Check every 1 second

        current_screenshot = capture_window(selected_window)
        if not monitoring or current_screenshot is None:
            break

        # Divide the images into tiles for comparison
        tile_size = 100  # Adjust tile size based on desired granularity
        last_tiles = divide_image_into_tiles(last_screenshot, tile_size)
        current_tiles = divide_image_into_tiles(current_screenshot, tile_size)

        # Create a copy of the current screenshot for overlay
        overlay_image = current_screenshot.copy()
        draw = ImageDraw.Draw(overlay_image)
        significant_change_detected = False

        # Check each tile for visual differences
        for (box1, last_tile), (box2, current_tile) in zip(last_tiles, current_tiles):
            diff = calculate_image_difference(last_tile, current_tile)
            CHANGE_THRESHOLD = 10  # Set tolerance for differences
            if diff > CHANGE_THRESHOLD:
                significant_change_detected = True
                print(f"Significant visual change detected in region {box1}: {diff}")
                # Highlight the changed region on the overlay image
                draw.rectangle(box1, outline="red", width=3)

        if significant_change_detected:
            play_sound()
            send_telegram_notification(overlay_image)

            # Stop monitoring and display the overlay
            monitoring = False
            update_status_indicator(False)
            display_overlay(overlay_image)

        last_screenshot = current_screenshot

def display_overlay(overlay_image):
    """Display the overlayed screenshot with highlighted changes and start auto-resume countdown."""
    root.deiconify()
    root.lift()
    root.update()

    overlay_window = Toplevel()
    overlay_window.title("Visual Changes Highlighted")
    overlay_window.attributes("-topmost", True)

    # Main frame
    main_frame = tk.Frame(overlay_window)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Image display
    overlay_photo = ImageTk.PhotoImage(overlay_image)
    overlay_label = tk.Label(main_frame, image=overlay_photo)
    overlay_label.image = overlay_photo
    overlay_label.pack()

    # Countdown frame
    countdown_frame = tk.Frame(overlay_window, bg="#f8f9fa")
    countdown_frame.pack(fill='x', pady=5)

    countdown_var = tk.StringVar()
    countdown_label = tk.Label(countdown_frame, 
                             textvariable=countdown_var, 
                             font=("Arial", 10),
                             bg="#f8f9fa")
    countdown_label.pack()

    user_response = {'action': None}

    def on_window_close():
        user_response['action'] = 'closed'
        overlay_window.destroy()

    def update_countdown(seconds_left):
        if seconds_left > 0 and user_response['action'] is None:
            countdown_var.set(f"Auto-resuming monitoring in {seconds_left} seconds...")
            overlay_window.after(1000, lambda: update_countdown(seconds_left - 1))
        elif user_response['action'] is None:
            # Auto-resume if user hasn't closed the window
            user_response['action'] = 'timeout'
            overlay_window.destroy()

    # Start countdown
    update_countdown(20)

    # Set window close handler
    overlay_window.protocol("WM_DELETE_WINDOW", on_window_close)

    # Wait for window to close
    overlay_window.wait_window()

    # Handle the result
    if user_response['action'] == 'closed':
        # User closed the window, show prompt
        prompt_restart_monitoring()
    else:
        # Auto-resumed due to timeout
        start_monitoring()

def prompt_restart_monitoring():
    """Prompt the user to restart monitoring."""
    response_window = Toplevel()
    response_window.title("Restart Monitoring")
    response_window.geometry("400x250")
    response_window.attributes('-topmost', True)

    frame = tk.Frame(response_window, padx=20, pady=20)
    frame.pack(fill=tk.BOTH, expand=True)

    label = tk.Label(frame, 
                    text="Would you like to restart monitoring?",
                    font=("Arial", 11))
    label.pack(pady=(0,30))

    def make_choice(choice):
        response_window.destroy()
        if choice:
            start_monitoring()
        else:
            stop_monitoring()

    btn_frame = tk.Frame(frame)
    btn_frame.pack(fill='x')

    tk.Button(btn_frame, 
              text="Yes",
              command=lambda: make_choice(True),
              bg="#28a745",
              fg="white",
              font=("Arial", 10, "bold"),
              relief="flat",
              cursor="hand2",
              padx=40,
              pady=10).pack(side=tk.LEFT, padx=20)

    tk.Button(btn_frame, 
              text="No",
              command=lambda: make_choice(False),
              bg="#dc3545",
              fg="white",
              font=("Arial", 10, "bold"),
              relief="flat",
              cursor="hand2",
              padx=40,
              pady=10).pack(side=tk.RIGHT, padx=20)

def update_status_indicator(active):
    """Update the status indicator (red/green circle)."""
    canvas.delete("all")
    color = "green" if active else "red"
    canvas.create_oval(10, 10, 40, 40, fill=color, outline=color)
    status_label.config(text="Monitoring..." if active else "Stopped", fg="green" if active else "red")

def start_monitoring():
    """Start monitoring the selected window."""
    global monitoring
    if not selected_window:
        messagebox.showerror("Error", "Please select a window first!")
        return

    # Check if Telegram is configured
    if not load_telegram_config():
        response = messagebox.askyesno("Telegram Not Configured", 
                                     "Telegram notifications are not configured. Would you like to configure them now?")
        if response:
            setup_telegram_config()
            return

    if not monitoring:
        monitoring = True
        update_status_indicator(True)
        thread = threading.Thread(target=monitor_window, daemon=True)
        thread.start()

def stop_monitoring():
    """Stop monitoring the selected window."""
    global monitoring
    monitoring = False
    update_status_indicator(False)

# Initialize tkinter application
root = tk.Tk()
root.title("Browser Monitor")
root.geometry("700x400")
root.configure(bg="#f8f9fa")

# Header Title
header = tk.Label(root, text="Browser Change Monitor", font=("Arial", 18, "bold"), bg="#f8f9fa", fg="#343a40")
header.pack(pady=10)

# Window Selection Section
selected_window_label = tk.Label(root, text="No browser window selected", wraplength=600, justify="center", 
                               font=("Arial", 10), bg="#f8f9fa", fg="#6c757d", relief="solid", bd=1)
selected_window_label.pack(pady=5, ipadx=10, ipady=10)

# Main Buttons Frame
main_button_frame = tk.Frame(root, bg="#f8f9fa")
main_button_frame.pack(pady=10)

# First row of buttons
first_row_frame = tk.Frame(main_button_frame, bg="#f8f9fa")
first_row_frame.pack(pady=(15, 15))

tk.Button(first_row_frame, 
         text="Select Window", 
         command=select_window, 
         font=("Arial", 10), 
         bg="#007bff", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(first_row_frame, 
         text="Start Monitoring", 
         command=start_monitoring, 
         font=("Arial", 10), 
         bg="#28a745", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(first_row_frame, 
         text="Stop Monitoring", 
         command=stop_monitoring, 
         font=("Arial", 10), 
         bg="#dc3545", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(first_row_frame, 
         text="Sound Test", 
         command=play_sound, 
         font=("Arial", 10), 
         bg="#6c757d", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

# Second row of buttons
second_row_frame = tk.Frame(main_button_frame, bg="#f8f9fa")
second_row_frame.pack(pady=(15, 0))

tk.Button(second_row_frame, 
         text="Telegram Setup", 
         command=setup_telegram_config, 
         font=("Arial", 10), 
         bg="#17a2b8", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(second_row_frame, 
         text="View Telegram Config", 
         command=view_telegram_config, 
         font=("Arial", 10), 
         bg="#6c757d", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(second_row_frame, 
         text="Test Telegram", 
         command=test_telegram_configuration, 
         font=("Arial", 10), 
         bg="#ffc107", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

tk.Button(second_row_frame, 
         text="Exit", 
         command=root.quit, 
         font=("Arial", 10), 
         bg="#343a40", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=10)

# Status Indicator Section
status_frame = tk.Frame(root, bg="#f8f9fa")
status_frame.pack(pady=(20, 15))

canvas = tk.Canvas(status_frame, width=50, height=50, bg="#f8f9fa", highlightthickness=0)
canvas.grid(row=0, column=0, padx=10)

status_label = tk.Label(status_frame, text="Stopped", font=("Arial", 12), bg="#f8f9fa", fg="red")
status_label.grid(row=0, column=1)

# Initialize status indicator as "Stopped"
update_status_indicator(False)

# Start the application
root.mainloop()
