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
import queue
from tkinter import ttk

# Initialize pygame mixer
pygame.mixer.init()

# Global variables
selected_window = None
monitoring = False
last_screenshot = None
selected_area = None
selection_window = None
show_monitored_area = False
command_queue = queue.Queue()  # For thread-safe command handling

def load_telegram_config():
    """Load Telegram configuration from a JSON file."""
    try:
        with open('telegram_config.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def send_telegram_message(message):
    """Send a simple text message via Telegram."""
    config = load_telegram_config()
    if not config:
        return

    try:
        bot_token = config['bot_token']
        chat_id = config['chat_id']

        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "HTML"
            }
        )
        if response.status_code != 200:
            print(f"Failed to send Telegram message: {response.text}")
    except Exception as e:
        print(f"Error sending Telegram message: {e}")

def check_telegram_commands():
    """Check for incoming Telegram commands."""
    global monitoring

    config = load_telegram_config()
    if not config:
        return

    try:
        bot_token = config['bot_token']
        last_update_id = 0

        while hasattr(check_telegram_commands, 'running') and check_telegram_commands.running:
            try:
                # Get updates from Telegram
                response = requests.get(
                    f"https://api.telegram.org/bot{bot_token}/getUpdates",
                    params={"offset": last_update_id + 1, "timeout": 30}
                )

                if response.status_code == 200:
                    updates = response.json()

                    if updates.get("ok") and updates.get("result"):
                        for update in updates["result"]:
                            last_update_id = update["update_id"]

                            if "message" in update and "text" in update["message"]:
                                command = update["message"]["text"].lower()

                                # Add command to queue for main thread processing
                                command_queue.put(command)

            except Exception as e:
                print(f"Error checking Telegram commands: {e}")

            time.sleep(1)

    except Exception as e:
        print(f"Error in command checking loop: {e}")

def process_telegram_commands():
    """Process any pending Telegram commands from the main thread."""
    try:
        while not command_queue.empty():
            command = command_queue.get_nowait()

            if command == "/start_monitoring":
                if not monitoring:
                    root.after(0, start_monitoring)
                    send_telegram_message("Monitoring started.")
                else:
                    send_telegram_message("Monitoring is already active.")

            elif command == "/stop_monitoring":
                if monitoring:
                    root.after(0, stop_monitoring)
                    send_telegram_message("Monitoring stopped.")
                else:
                    send_telegram_message("Monitoring is already stopped.")

            elif command == "/status":
                status = "active" if monitoring else "stopped"
                send_telegram_message(f"Monitoring is currently {status}.")

            elif command == "/help":
                help_text = """
Available commands:
/start_monitoring - Start monitoring
/stop_monitoring - Stop monitoring
/status - Check monitoring status
/help - Show this help message
"""
                send_telegram_message(help_text)
    except Exception as e:
        print(f"Error processing Telegram commands: {e}")
    finally:
        # Schedule next check
        root.after(1000, process_telegram_commands)

def start_telegram_command_checker():
    """Start the Telegram command checking thread."""
    check_telegram_commands.running = True
    thread = threading.Thread(target=check_telegram_commands, daemon=True)
    thread.start()
    # Start command processing in main thread
    root.after(1000, process_telegram_commands)

def stop_telegram_command_checker():
    """Stop the Telegram command checking thread."""
    if hasattr(check_telegram_commands, 'running'):
        check_telegram_commands.running = False
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

    Available commands after setup:
    /start_monitoring - Start monitoring
    /stop_monitoring - Stop monitoring
    /status - Check monitoring status
    /help - Show command list
    """
    tk.Label(main_frame, text=instructions, justify=tk.LEFT, wraplength=450).pack(pady=(0,20))

    # Bot Token section
    bot_frame = tk.Frame(main_frame)
    bot_frame.pack(fill='x', pady=(0,10))

    tk.Label(bot_frame, text="Bot Token:", anchor='w').pack(side=tk.LEFT)

    token_var = tk.StringVar()
    token_entry = tk.Entry(bot_frame, width=45, show="●", textvariable=token_var)
    token_entry.pack(side=tk.LEFT, padx=5)

    token_visible = False
    def toggle_token():
        nonlocal token_visible
        token_visible = not token_visible
        token_entry.config(show="" if token_visible else "●")
        token_button.config(text="Hide" if token_visible else "Show")

    token_button = tk.Button(bot_frame, text="Show", command=toggle_token,
                            bg="#6c757d", fg="white", relief="flat", padx=10)
    token_button.pack(side=tk.LEFT)

    # Chat ID section
    chat_frame = tk.Frame(main_frame)
    chat_frame.pack(fill='x', pady=(0,20))

    tk.Label(chat_frame, text="Chat ID:  ", anchor='w').pack(side=tk.LEFT)

    chat_var = tk.StringVar()
    chat_entry = tk.Entry(chat_frame, width=45, show="●", textvariable=chat_var)
    chat_entry.pack(side=tk.LEFT, padx=5)

    chat_visible = False
    def toggle_chat():
        nonlocal chat_visible
        chat_visible = not chat_visible
        chat_entry.config(show="" if chat_visible else "●")
        chat_button.config(text="Hide" if chat_visible else "Show")

    chat_button = tk.Button(chat_frame, text="Show", command=toggle_chat,
                           bg="#6c757d", fg="white", relief="flat", padx=10)
    chat_button.pack(side=tk.LEFT)

    # Load existing config if any
    config = load_telegram_config()
    if config:
        token_var.set(config.get('bot_token', ''))
        chat_var.set(config.get('chat_id', ''))

    def save_config():
        config = {
            'bot_token': token_var.get().strip(),
            'chat_id': chat_var.get().strip()
        }

        # Validate inputs
        if not config['bot_token'] or not config['chat_id']:
            messagebox.showerror("Error", "Both Bot Token and Chat ID are required!")
            return

        try:
            with open('telegram_config.json', 'w') as f:
                json.dump(config, f)

            # Test the configuration
            test_message = "Configuration test - If you receive this, your setup is working correctly!"
            send_telegram_message(test_message)

            config_window.destroy()
            messagebox.showinfo("Success", "Telegram configuration saved and tested!")
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
    config_window.geometry("400x350")  # Made taller for command list

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

    # Show available commands
    tk.Label(frame, text="\nAvailable Commands:", font=("Arial", 10, "bold")).pack(anchor='w', pady=(20,5))
    commands = """
    /start_monitoring - Start monitoring
    /stop_monitoring - Stop monitoring
    /status - Check monitoring status
    /help - Show command list
    """
    tk.Label(frame, text=commands, justify=tk.LEFT).pack(anchor='w', padx=20)

    def remove_configuration():
        if messagebox.askyesno("Confirm", "Are you sure you want to remove the current configuration?"):
            try:
                if os.path.exists('telegram_config.json'):
                    os.remove('telegram_config.json')
                messagebox.showinfo("Success", "Configuration removed successfully!")
                config_window.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to remove configuration: {str(e)}")

    # Button frame
    button_frame = tk.Frame(frame)
    button_frame.pack(pady=20)

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
            # Save the image temporarily with unique timestamp
            temp_image_path = f"temp_screenshot_{int(time.time())}.png"
            overlay_image.save(temp_image_path)

            try:
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
            finally:
                # Clean up temporary file
                try:
                    if os.path.exists(temp_image_path):
                        os.remove(temp_image_path)
                except Exception as e:
                    print(f"Error removing temporary file: {e}")

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

Available commands:
• /start_monitoring - Start monitoring
• /stop_monitoring - Stop monitoring
• /status - Check monitoring status
• /help - Show this help message
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
        win for win in windows if win.title and any(browser in win.title.lower() for browser in 
        ["chrome", "firefox", "brave", "vivaldi", "edge", "opera"])
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

    # Add instructions
    tk.Label(selection_window, 
            text="Select the browser window you want to monitor:",
            font=("Arial", 10),
            pady=10).pack()

    button_frame = tk.Frame(selection_window)
    button_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    for win in windows:
        btn = tk.Button(button_frame, 
                       text=win.title, 
                       anchor="w",
                       command=lambda w=win: set_selected_window(w, selection_window),
                       relief="flat",
                       cursor="hand2",
                       bg="#f8f9fa",
                       pady=5)
        btn.pack(fill=tk.X, padx=5, pady=2, ipadx=5)
def set_selected_window(window, selection_window):
    """Set the selected window for monitoring."""
    global selected_window, selected_area
    selected_window = window
    selected_area = None  # Reset selected area when new window is selected
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
    """Capture a screenshot of the selected window, working even with display off."""
    if not window:
        return None
    try:
        # Direct screen capture without window activation
        with mss.mss() as sct:
            try:
                # Get window coordinates
                left = max(0, window.left)
                top = max(0, window.top)
                width = window.width
                height = window.height

                # Create monitor dict for capture
                monitor = {
                    "left": left,
                    "top": top,
                    "width": width,
                    "height": height
                }

                # Capture without trying to activate window
                screenshot = sct.grab(monitor)
                img = Image.frombytes("RGB", (screenshot.width, screenshot.height), screenshot.rgb)
                return img
            except Exception as e:
                print(f"Screenshot capture error: {e}")
                return None
    except Exception as e:
        print(f"Capture error: {e}")
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
    """Continuously monitor the selected window or area for visual changes."""
    global monitoring, last_screenshot

    if not selected_window:
        messagebox.showerror("Error", "No window selected!")
        return

    # Capture the initial screenshot for comparison
    full_screenshot = capture_window(selected_window)
    if full_screenshot is None:
        messagebox.showerror("Error", "Could not capture the selected window.")
        return

    # If area is selected, crop the screenshot
    if selected_area:
        last_screenshot = full_screenshot.crop(selected_area)
    else:
        last_screenshot = full_screenshot

    consecutive_failures = 0
    MAX_FAILURES = 3
    notification_sent = False  # Flag to prevent multiple notifications

    while monitoring:
        try:
            time.sleep(1)

            if not monitoring:  # Check monitoring status
                break

            current_full_screenshot = capture_window(selected_window)
            if current_full_screenshot is None:
                consecutive_failures += 1
                if consecutive_failures >= MAX_FAILURES:
                    print("Multiple capture failures, but continuing to monitor...")
                continue
            else:
                consecutive_failures = 0

            # If area is selected, crop the current screenshot
            if selected_area:
                current_screenshot = current_full_screenshot.crop(selected_area)
            else:
                current_screenshot = current_full_screenshot

            # Only proceed if not already notified
            if not notification_sent:
                # Divide the images into tiles for comparison
                tile_size = 100
                last_tiles = divide_image_into_tiles(last_screenshot, tile_size)
                current_tiles = divide_image_into_tiles(current_screenshot, tile_size)

                overlay_image = current_screenshot.copy()
                draw = ImageDraw.Draw(overlay_image)
                significant_change_detected = False

                for (box1, last_tile), (box2, current_tile) in zip(last_tiles, current_tiles):
                    if not monitoring:  # Check monitoring status during comparison
                        return
                    diff = calculate_image_difference(last_tile, current_tile)
                    CHANGE_THRESHOLD = 10
                    if diff > CHANGE_THRESHOLD:
                        significant_change_detected = True
                        draw.rectangle(box1, outline="red", width=3)

                if significant_change_detected:
                    # Set notification flag before sending
                    notification_sent = True

                    # Prepare final overlay image
                    final_overlay = None
                    if selected_area:
                        final_overlay = current_full_screenshot.copy()
                        draw = ImageDraw.Draw(final_overlay)
                        draw.rectangle(selected_area, outline="blue", width=2)
                        final_overlay.paste(overlay_image, (selected_area[0], selected_area[1]))
                    else:
                        final_overlay = overlay_image

                    # Stop monitoring and send notifications
                    monitoring = False
                    update_status_indicator(False)
                    play_sound()
                    send_telegram_notification(final_overlay)
                    display_overlay(final_overlay)
                    return  # Exit function completely

            if monitoring:  # Only update if still monitoring
                last_screenshot = current_screenshot

        except Exception as e:
            print(f"Error in monitoring loop: {e}")
            time.sleep(1)
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
            # Reset monitoring state before restarting
            global monitoring, last_screenshot
            monitoring = False
            last_screenshot = None
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
    status_label.config(text="Monitoring..." if active else "Stopped", fg=color)

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

        # Start command checker if not already running
        if not hasattr(check_telegram_commands, 'running'):
            start_telegram_command_checker()

        thread = threading.Thread(target=monitor_window, daemon=True)
        thread.start()

def stop_monitoring():
    """Stop monitoring the selected window."""
    global monitoring
    monitoring = False
    update_status_indicator(False)

def toggle_area_highlight():
    """Toggle the highlight of the monitored area."""
    global show_monitored_area

    if not selected_window:
        messagebox.showinfo("Info", "Please select a window first!")
        return

    if not selected_area:
        messagebox.showinfo("Info", "No area is currently selected for monitoring.\nUse 'Select Area' to define an area first.")
        return

    show_monitored_area = not show_monitored_area

    if show_monitored_area:
        # Show the highlighted area
        screenshot = capture_window(selected_window)
        if screenshot:
            highlight_window = Toplevel()
            highlight_window.title("Monitored Area")
            highlight_window.attributes('-topmost', True)

            # Create canvas and draw screenshot with highlight
            photo = ImageTk.PhotoImage(screenshot)
            canvas = tk.Canvas(highlight_window, width=screenshot.width, height=screenshot.height)
            canvas.pack()
            canvas.create_image(0, 0, image=photo, anchor='nw')
            canvas.image = photo  # Keep reference

            # Draw rectangle around monitored area
            canvas.create_rectangle(selected_area[0], selected_area[1],
                                 selected_area[2], selected_area[3],
                                 outline='blue', width=2)

            def on_close():
                global show_monitored_area
                show_monitored_area = False
                highlight_window.destroy()

            highlight_window.protocol("WM_DELETE_WINDOW", on_close)
    else:
        # Close all toplevel windows that might be showing the highlight
        for widget in root.winfo_children():
            if isinstance(widget, Toplevel) and widget.title() == "Monitored Area":
                widget.destroy()
def select_monitoring_area():
    """Allow user to select a specific area of the window to monitor."""
    global selected_area, selection_window, selected_window

    if not selected_window:
        messagebox.showerror("Error", "Please select a window first!")
        return

    # Capture current window
    screenshot = capture_window(selected_window)
    if screenshot is None:
        messagebox.showerror("Error", "Could not capture window!")
        return

    # Create selection window
    selection_window = Toplevel()
    selection_window.title("Select Area to Monitor")
    selection_window.attributes('-topmost', True)

    # Add instructions label
    instructions = """
    Click and drag to select the area you want to monitor.
    The selected area will be outlined in red.
    """
    tk.Label(selection_window, text=instructions, justify=tk.LEFT, pady=10).pack()

    # Convert PIL image to PhotoImage
    photo = ImageTk.PhotoImage(screenshot)

    # Create canvas for selection
    canvas = tk.Canvas(selection_window, width=screenshot.width, height=screenshot.height)
    canvas.pack()

    # Display screenshot on canvas
    canvas.create_image(0, 0, image=photo, anchor='nw')
    canvas.image = photo  # Keep reference

    # Variables for selection rectangle
    start_x = start_y = 0
    rect_id = None
    selection_started = False

    def start_selection(event):
        nonlocal start_x, start_y, rect_id, selection_started
        start_x, start_y = event.x, event.y
        if rect_id:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, 
                                        outline='red', width=2)
        selection_started = True

    def update_selection(event):
        nonlocal rect_id, selection_started
        if selection_started:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def end_selection(event):
        nonlocal selection_started
        global selected_area
        if selection_started:
            selection_started = False
            # Get the coordinates in the correct order (top-left to bottom-right)
            x1, y1 = min(start_x, event.x), min(start_y, event.y)
            x2, y2 = max(start_x, event.x), max(start_y, event.y)

            # Ensure minimum size
            if abs(x2 - x1) < 10 or abs(y2 - y1) < 10:
                messagebox.showwarning("Warning", "Selected area is too small. Please select a larger area.")
                return

            # Store selected area
            selected_area = (x1, y1, x2, y2)

            # Show confirmation buttons
            show_confirmation_buttons()

    def show_confirmation_buttons():
        """Show confirmation buttons after area selection."""
        button_frame = tk.Frame(selection_window)
        button_frame.pack(pady=10)

        # Add area dimensions label
        if selected_area:
            width = selected_area[2] - selected_area[0]
            height = selected_area[3] - selected_area[1]
            tk.Label(button_frame, 
                    text=f"Selected Area: {width}x{height} pixels",
                    font=("Arial", 10)).pack(pady=(0, 10))

        tk.Button(button_frame, text="Confirm Selection",
                 command=confirm_selection,
                 bg="#28a745", fg="white",
                 font=("Arial", 10),
                 relief="flat", cursor="hand2",
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Reset Selection",
                 command=reset_selection,
                 bg="#ffc107", fg="white",
                 font=("Arial", 10),
                 relief="flat", cursor="hand2",
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Cancel",
                 command=selection_window.destroy,
                 bg="#dc3545", fg="white",
                 font=("Arial", 10),
                 relief="flat", cursor="hand2",
                 padx=20, pady=5).pack(side=tk.LEFT, padx=5)

    def confirm_selection():
        global selected_area
        if selected_area:
            if monitoring:
                # If currently monitoring, ask to restart
                if messagebox.askyesno("Restart Required", 
                                     "Changing the monitored area requires restarting the monitoring. Continue?"):
                    stop_monitoring()
                    selection_window.destroy()
                    messagebox.showinfo("Success", "Area selected successfully! You can now restart monitoring.")
                else:
                    return
            else:
                selection_window.destroy()
                messagebox.showinfo("Success", "Area selected successfully!")
        else:
            messagebox.showerror("Error", "Please select an area first!")

    def reset_selection():
        """Reset the selection and remove the rectangle."""
        global selected_area
        nonlocal rect_id
        selected_area = None
        if rect_id:
            canvas.delete(rect_id)
            rect_id = None
        # Remove confirmation buttons if they exist
        for widget in selection_window.winfo_children():
            if isinstance(widget, tk.Frame) and widget != canvas:
                widget.destroy()

    # Bind mouse events
    canvas.bind('<Button-1>', start_selection)
    canvas.bind('<B1-Motion>', update_selection)
    canvas.bind('<ButtonRelease-1>', end_selection)

def on_closing():
    """Handle application closing."""
    if monitoring:
        if not messagebox.askyesno("Confirm Exit", 
                                  "Monitoring is still active. Are you sure you want to exit?"):
            return
    stop_telegram_command_checker()
    root.quit()
def open_alert_settings():
    """Open a window to configure alert settings"""
    settings_window = tk.Toplevel(root)
    settings_window.title("Alert Settings")
    settings_window.geometry("400x500")
    settings_window.configure(bg="#f8f9fa")

    # Load existing settings or use defaults
    try:
        with open('alert_settings.json', 'r') as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {
            'min_change_percent': 5,
            'cooldown_period': 60,
            'notification_sound': True,
            'telegram_alerts': True,
            'desktop_notifications': True
        }

    # Create settings controls
    tk.Label(settings_window, text="Alert Settings", font=("Arial", 14, "bold"), 
            bg="#f8f9fa").pack(pady=10)

    # Minimum change percentage
    tk.Label(settings_window, text="Minimum change percentage to trigger alert:", 
            bg="#f8f9fa").pack(pady=5)
    change_scale = ttk.Scale(settings_window, from_=1, to=50, 
                            value=settings['min_change_percent'])
    change_scale.pack()

    # Cooldown period
    tk.Label(settings_window, text="Cooldown period between alerts (seconds):", 
            bg="#f8f9fa").pack(pady=5)
    cooldown_scale = ttk.Scale(settings_window, from_=10, to=300, 
                              value=settings['cooldown_period'])
    cooldown_scale.pack()

    # Checkboxes for notification types
    sound_var = tk.BooleanVar(value=settings['notification_sound'])
    tk.Checkbutton(settings_window, text="Play sound on alert", variable=sound_var, 
                   bg="#f8f9fa").pack(pady=5)

    telegram_var = tk.BooleanVar(value=settings['telegram_alerts'])
    tk.Checkbutton(settings_window, text="Send Telegram notifications", 
                   variable=telegram_var, bg="#f8f9fa").pack(pady=5)

    desktop_var = tk.BooleanVar(value=settings['desktop_notifications'])
    tk.Checkbutton(settings_window, text="Show desktop notifications", 
                   variable=desktop_var, bg="#f8f9fa").pack(pady=5)

    def save_settings():
        settings = {
            'min_change_percent': change_scale.get(),
            'cooldown_period': cooldown_scale.get(),
            'notification_sound': sound_var.get(),
            'telegram_alerts': telegram_var.get(),
            'desktop_notifications': desktop_var.get()
        }
        with open('alert_settings.json', 'w') as f:
            json.dump(settings, f)
        settings_window.destroy()

    # Save button
    tk.Button(settings_window, text="Save Settings", command=save_settings,
              bg="#28a745", fg="white", font=("Arial", 10),
              relief="flat", cursor="hand2", padx=10, pady=5).pack(pady=20)

# Initialize tkinter application
root = tk.Tk()
root.title("Browser Monitor")
root.geometry("800x475")
root.configure(bg="#f8f9fa")

# Set program icon (if available)
try:
    root.iconbitmap('monitor_icon.ico')
except:
    pass

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

# First row of buttons - Core Functions
first_row_frame = tk.Frame(main_button_frame, bg="#f8f9fa")
first_row_frame.pack(pady=(15, 15))  # Equal padding top and bottom

# Core functionality buttons
tk.Button(first_row_frame, 
         text="Select Window", 
         command=select_window, 
         font=("Arial", 10), 
         bg="#007bff", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(first_row_frame, 
         text="Start Monitoring", 
         command=start_monitoring, 
         font=("Arial", 10), 
         bg="#28a745", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(first_row_frame, 
         text="Stop Monitoring", 
         command=stop_monitoring, 
         font=("Arial", 10), 
         bg="#dc3545", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

# Second row of buttons - Telegram Configuration
second_row_frame = tk.Frame(main_button_frame, bg="#f8f9fa")
second_row_frame.pack(pady=(15, 15))  # Equal padding top and bottom

tk.Button(second_row_frame, 
         text="Telegram Setup", 
         command=setup_telegram_config, 
         font=("Arial", 10), 
         bg="#17a2b8", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(second_row_frame, 
         text="View Telegram Config", 
         command=view_telegram_config, 
         font=("Arial", 10), 
         bg="#6c757d", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(second_row_frame, 
         text="Test Telegram", 
         command=test_telegram_configuration, 
         font=("Arial", 10), 
         bg="#ffc107", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(second_row_frame,
         text="Alert Settings",
         command=open_alert_settings,
         font=("Arial", 10),
         bg="#17a2b8",
         fg="white",
         relief="flat",
         cursor="hand2",
         padx=10,
         pady=5).pack(side=tk.LEFT, padx=20)

# Third row of buttons - Utilities
third_row_frame = tk.Frame(main_button_frame, bg="#f8f9fa")
third_row_frame.pack(pady=(15, 15))  # Equal padding top and bottom

tk.Button(third_row_frame, 
         text="Select Area", 
         command=select_monitoring_area, 
         font=("Arial", 10), 
         bg="#17a2b8", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(third_row_frame, 
         text="Show/Hide Area", 
         command=toggle_area_highlight, 
         font=("Arial", 10), 
         bg="#6c757d", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(third_row_frame, 
         text="Sound Test", 
         command=play_sound, 
         font=("Arial", 10), 
         bg="#6c757d", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

tk.Button(third_row_frame, 
         text="Exit", 
         command=on_closing, 
         font=("Arial", 10), 
         bg="#343a40", 
         fg="white", 
         relief="flat", 
         cursor="hand2", 
         padx=10, 
         pady=5).pack(side=tk.LEFT, padx=20)

# Status Indicator Section
status_frame = tk.Frame(root, bg="#f8f9fa")
status_frame.pack(pady=(20, 15))

canvas = tk.Canvas(status_frame, width=50, height=50, bg="#f8f9fa", highlightthickness=0)
canvas.grid(row=0, column=0, padx=10)

status_label = tk.Label(status_frame, text="Stopped", font=("Arial", 12), bg="#f8f9fa", fg="red")
status_label.grid(row=0, column=1)

# Initialize status indicator as "Stopped"
update_status_indicator(False)

# Set window close handler
root.protocol("WM_DELETE_WINDOW", on_closing)

# Start checking for Telegram commands if configured
if load_telegram_config():
    start_telegram_command_checker()

# Start the application
root.mainloop()
