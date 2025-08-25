#!/usr/bin/env python3
"""
Upload Assistant GUI Manager - Midnight Commander style interface
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
import os
import subprocess
import json
import configparser
from pathlib import Path
from typing import List, Dict, Optional
import threading

class UAConfig:
    """Configuration manager for the application"""
    
    def __init__(self):
        self.config_file = Path.home() / ".ua_gui_config.ini"
        self.config = configparser.ConfigParser()
        self.load_config()
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            self.config.read(self.config_file)
        else:
            # Set default values
            self.config['PATHS'] = {
                'logs_dir': '/mnt/user/appdata/cross-pollinator/logs',
                'torrents_dir': '/mnt/user/data/torrents',
                'upload_assistant_path': 'upload-assistant'
            }
            self.config['UA_ARGS'] = {
                'tmdb': '',
                'imdb': '',
                'mal': '',
                'category': '',
                'type': '',
                'source': '',
                'edition': '',
                'resolution': '',
                'freeleech': 'false',
                'tag': '',
                'region': '',
                'season': '',
                'episode': '',
                'daily': 'false',
                'no_dupe': 'false',
                'skip_imghost': 'false',
                'personalrelease': 'false'
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            self.config.write(f)
    
    def get(self, section: str, key: str, fallback: str = '') -> str:
        return self.config.get(section, key, fallback=fallback)
    
    def set(self, section: str, key: str, value: str):
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value
        self.save_config()

class FilterPanel:
    """Left panel for filters and navigation"""
    
    def __init__(self, parent, config: UAConfig, on_selection_change):
        self.config = config
        self.on_selection_change = on_selection_change
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # Filters section
        filters_frame = ttk.LabelFrame(self.frame, text="Filters", padding=5)
        filters_frame.pack(fill="both", expand=False, padx=5, pady=5)
        
        # Missing torrents filter
        self.missing_torrents_var = tk.BooleanVar()
        missing_cb = ttk.Checkbutton(filters_frame, text="Show Missing Torrents", 
                                   variable=self.missing_torrents_var,
                                   command=self.on_filter_change)
        missing_cb.pack(anchor="w")
        
        # Directory navigation
        nav_frame = ttk.LabelFrame(self.frame, text="Directory Navigation", padding=5)
        nav_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Current path display
        self.current_path_var = tk.StringVar(value=self.config.get('PATHS', 'torrents_dir'))
        path_frame = ttk.Frame(nav_frame)
        path_frame.pack(fill="x", pady=(0, 5))
        ttk.Label(path_frame, text="Path:").pack(side="left")
        path_entry = ttk.Entry(path_frame, textvariable=self.current_path_var, state="readonly")
        path_entry.pack(side="left", fill="x", expand=True, padx=(5, 0))
        
        # Change directory button
        ttk.Button(path_frame, text="...", command=self.change_directory, width=3).pack(side="right")
        
        # Directory tree
        self.dir_tree = ttk.Treeview(nav_frame, height=15)
        self.dir_tree.pack(fill="both", expand=True)
        self.dir_tree.bind("<<TreeviewSelect>>", self.on_dir_select)
        
        # Scrollbar for tree
        tree_scroll = ttk.Scrollbar(nav_frame, orient="vertical", command=self.dir_tree.yview)
        tree_scroll.pack(side="right", fill="y")
        self.dir_tree.configure(yscrollcommand=tree_scroll.set)
        
        # Load initial directory
        self.refresh_directory_tree()
    
    def change_directory(self):
        """Change the base directory"""
        new_dir = filedialog.askdirectory(initialdir=self.current_path_var.get(),
                                         title="Select Torrents Directory")
        if new_dir:
            self.current_path_var.set(new_dir)
            self.config.set('PATHS', 'torrents_dir', new_dir)
            self.refresh_directory_tree()
    
    def refresh_directory_tree(self):
        """Refresh the directory tree"""
        self.dir_tree.delete(*self.dir_tree.get_children())
        base_path = self.current_path_var.get()
        
        if os.path.exists(base_path):
            self.populate_tree("", base_path)
    
    def populate_tree(self, parent, path):
        """Populate tree with subdirectories"""
        try:
            items = []
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    items.append((item, item_path))
            
            items.sort()
            for item, item_path in items:
                node = self.dir_tree.insert(parent, "end", text=item, values=(item_path,))
                # Check if directory has subdirectories
                try:
                    if any(os.path.isdir(os.path.join(item_path, x)) for x in os.listdir(item_path)):
                        self.dir_tree.insert(node, "end", text="Loading...")
                except PermissionError:
                    pass
        except PermissionError:
            pass
    
    def on_dir_select(self, event):
        """Handle directory selection"""
        selection = self.dir_tree.selection()
        if selection:
            item = selection[0]
            values = self.dir_tree.item(item, "values")
            if values:
                selected_path = values[0]
                self.on_selection_change(selected_path)
                
                # Expand directory if it hasn't been expanded yet
                children = self.dir_tree.get_children(item)
                if len(children) == 1 and self.dir_tree.item(children[0], "text") == "Loading...":
                    self.dir_tree.delete(children[0])
                    self.populate_tree(item, selected_path)
    
    def on_filter_change(self):
        """Handle filter changes"""
        # Notify parent of filter change
        self.on_selection_change(self.get_selected_path())
    
    def get_selected_path(self) -> str:
        """Get currently selected path"""
        selection = self.dir_tree.selection()
        if selection:
            values = self.dir_tree.item(selection[0], "values")
            if values:
                return values[0]
        return self.current_path_var.get()
    
    def get_missing_torrents_filter(self) -> bool:
        """Check if missing torrents filter is enabled"""
        return self.missing_torrents_var.get()

class FilePanel:
    """Right panel for file listing and operations"""
    
    def __init__(self, parent, config: UAConfig):
        self.config = config
        self.current_files = []
        
        # Create main frame
        self.frame = ttk.Frame(parent)
        
        # File list
        list_frame = ttk.LabelFrame(self.frame, text="Files", padding=5)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # File listbox with scrollbar
        list_container = ttk.Frame(list_frame)
        list_container.pack(fill="both", expand=True)
        
        self.file_listbox = tk.Listbox(list_container, selectmode="single")
        self.file_listbox.pack(side="left", fill="both", expand=True)
        
        list_scroll = ttk.Scrollbar(list_container, orient="vertical", command=self.file_listbox.yview)
        list_scroll.pack(side="right", fill="y")
        self.file_listbox.configure(yscrollcommand=list_scroll.set)
        
        # Action buttons
        button_frame = ttk.Frame(self.frame)
        button_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(button_frame, text="Rename", command=self.rename_file).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Upload Assistant", command=self.launch_upload_assistant).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Make Torrent", command=self.make_torrent).pack(side="left", padx=2)
        ttk.Button(button_frame, text="Refresh", command=self.refresh_files).pack(side="right", padx=2)
    
    def update_files(self, directory: str, show_missing_only: bool = False):
        """Update file list for given directory"""
        self.current_directory = directory
        self.file_listbox.delete(0, tk.END)
        self.current_files = []
        
        if not os.path.exists(directory):
            return
        
        try:
            if show_missing_only:
                # Load missing torrents from logs
                self.load_missing_torrents()
            else:
                # Load all files in directory
                files = []
                for item in os.listdir(directory):
                    item_path = os.path.join(directory, item)
                    if os.path.isfile(item_path) or os.path.isdir(item_path):
                        files.append(item)
                
                files.sort()
                for file in files:
                    self.file_listbox.insert(tk.END, file)
                    self.current_files.append(os.path.join(directory, file))
        except PermissionError:
            messagebox.showerror("Error", f"Permission denied accessing: {directory}")
    
    def load_missing_torrents(self):
        """Load missing torrents from cross-pollinator logs"""
        logs_dir = self.config.get('PATHS', 'logs_dir')
        if not os.path.exists(logs_dir):
            messagebox.showwarning("Warning", f"Logs directory not found: {logs_dir}")
            return
        
        # This is a placeholder - implement actual log parsing based on your log format
        try:
            # Look for log files
            log_files = [f for f in os.listdir(logs_dir) if f.endswith('.log')]
            missing_files = []
            
            for log_file in log_files:
                log_path = os.path.join(logs_dir, log_file)
                try:
                    with open(log_path, 'r') as f:
                        content = f.read()
                        # Parse for missing torrent patterns - adjust this based on your log format
                        lines = content.split('\n')
                        for line in lines:
                            if 'missing' in line.lower() and 'torrent' in line.lower():
                                # Extract filename from log line - adjust parsing as needed
                                missing_files.append(line.strip())
                except Exception as e:
                    print(f"Error reading log file {log_file}: {e}")
            
            for missing in missing_files:
                self.file_listbox.insert(tk.END, f"[MISSING] {missing}")
                self.current_files.append(missing)
                
        except Exception as e:
            messagebox.showerror("Error", f"Error loading missing torrents: {e}")
    
    def get_selected_file(self) -> Optional[str]:
        """Get currently selected file"""
        selection = self.file_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.current_files):
                return self.current_files[index]
        return None
    
    def rename_file(self):
        """Rename selected file"""
        selected_file = self.get_selected_file()
        if not selected_file:
            messagebox.showwarning("Warning", "Please select a file to rename")
            return
        
        old_name = os.path.basename(selected_file)
        new_name = simpledialog.askstring("Rename File", f"Enter new name for '{old_name}':", 
                                        initialvalue=old_name)
        
        if new_name and new_name != old_name:
            try:
                old_path = selected_file
                new_path = os.path.join(os.path.dirname(selected_file), new_name)
                os.rename(old_path, new_path)
                self.refresh_files()
                messagebox.showinfo("Success", f"Renamed '{old_name}' to '{new_name}'")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to rename file: {e}")
    
    def launch_upload_assistant(self):
        """Launch upload assistant with custom arguments"""
        selected_file = self.get_selected_file()
        if not selected_file:
            messagebox.showwarning("Warning", "Please select a file for upload assistant")
            return
        
        # Open UA arguments dialog
        ua_dialog = UAArgsDialog(self.frame, self.config, selected_file)
        if ua_dialog.result:
            # Launch UA in terminal
            self.execute_upload_assistant(selected_file, ua_dialog.result)
    
    def make_torrent(self):
        """Create torrent using torf"""
        selected_file = self.get_selected_file()
        if not selected_file:
            messagebox.showwarning("Warning", "Please select a file to create torrent for")
            return
        
        messagebox.showinfo("Info", "Torrent creation functionality will be implemented")
    
    def refresh_files(self):
        """Refresh current file listing"""
        if hasattr(self, 'current_directory'):
            self.update_files(self.current_directory)
    
    def execute_upload_assistant(self, file_path: str, args: Dict[str, str]):
        """Execute upload assistant with given arguments"""
        ua_path = self.config.get('PATHS', 'upload_assistant_path')
        
        # Build command
        cmd = [ua_path, file_path]
        for key, value in args.items():
            if value:  # Only add non-empty values
                if isinstance(value, bool):
                    if value:
                        cmd.append(f"--{key}")
                else:
                    cmd.extend([f"--{key}", str(value)])
        
        # Launch in new terminal
        try:
            if os.name == 'nt':  # Windows
                subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k'] + cmd)
            else:  # Unix-like
                # Try different terminal emulators
                terminals = ['gnome-terminal', 'xterm', 'konsole', 'terminator']
                for terminal in terminals:
                    try:
                        if terminal == 'gnome-terminal':
                            subprocess.Popen([terminal, '--', 'bash', '-c', ' '.join(cmd) + '; read -p "Press Enter to continue..."'])
                        else:
                            subprocess.Popen([terminal, '-e', 'bash', '-c', ' '.join(cmd) + '; read -p "Press Enter to continue..."'])
                        break
                    except FileNotFoundError:
                        continue
                else:
                    # Fallback: run in current terminal
                    subprocess.run(cmd)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch upload assistant: {e}")

class UAArgsDialog:
    """Dialog for configuring upload assistant arguments"""
    
    def __init__(self, parent, config: UAConfig, file_path: str):
        self.config = config
        self.file_path = file_path
        self.result = None
        
        # Create dialog window
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Upload Assistant Arguments")
        self.dialog.geometry("600x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (600 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (500 // 2)
        self.dialog.geometry(f"600x500+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create dialog widgets"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # File info
        info_frame = ttk.LabelFrame(main_frame, text="File Information", padding=5)
        info_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(info_frame, text=f"File: {os.path.basename(self.file_path)}").pack(anchor="w")
        ttk.Label(info_frame, text=f"Path: {self.file_path}").pack(anchor="w")
        
        # Arguments frame with scrollbar
        args_frame = ttk.LabelFrame(main_frame, text="Upload Assistant Arguments", padding=5)
        args_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create scrollable frame
        canvas = tk.Canvas(args_frame)
        scrollbar = ttk.Scrollbar(args_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Argument widgets
        self.arg_vars = {}
        self.create_arg_widgets(scrollable_frame)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Launch", command=self.launch).pack(side="right")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
    
    def create_arg_widgets(self, parent):
        """Create widgets for each UA argument"""
        ua_args = {
            'tmdb': 'TMDB ID',
            'imdb': 'IMDB ID', 
            'mal': 'MyAnimeList ID',
            'category': 'Category',
            'type': 'Type (DISC, REMUX, ENCODE, WEBDL, WEBRIP, HDTV)',
            'source': 'Source',
            'edition': 'Edition',
            'resolution': 'Resolution',
            'tag': 'Group Tag',
            'region': 'Region',
            'season': 'Season Number',
            'episode': 'Episode Number'
        }
        
        boolean_args = {
            'freeleech': 'Free Leech',
            'daily': 'Daily Episode',
            'no_dupe': 'No Duplicate Check',
            'skip_imghost': 'Skip Image Hosting',
            'personalrelease': 'Personal Release'
        }
        
        row = 0
        
        # Text arguments
        for arg_key, label in ua_args.items():
            ttk.Label(parent, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=(0, 10), pady=2)
            var = tk.StringVar(value=self.config.get('UA_ARGS', arg_key))
            entry = ttk.Entry(parent, textvariable=var, width=40)
            entry.grid(row=row, column=1, sticky="ew", pady=2)
            self.arg_vars[arg_key] = var
            row += 1
        
        # Boolean arguments
        ttk.Separator(parent, orient='horizontal').grid(row=row, column=0, columnspan=2, sticky="ew", pady=10)
        row += 1
        
        for arg_key, label in boolean_args.items():
            var = tk.BooleanVar(value=self.config.get('UA_ARGS', arg_key) == 'true')
            cb = ttk.Checkbutton(parent, text=label, variable=var)
            cb.grid(row=row, column=0, columnspan=2, sticky="w", pady=2)
            self.arg_vars[arg_key] = var
            row += 1
        
        # Configure column weights
        parent.grid_columnconfigure(1, weight=1)
    
    def launch(self):
        """Launch with current arguments"""
        # Save current values to config
        for key, var in self.arg_vars.items():
            if isinstance(var, tk.BooleanVar):
                self.config.set('UA_ARGS', key, 'true' if var.get() else 'false')
            else:
                self.config.set('UA_ARGS', key, var.get())
        
        # Prepare result
        self.result = {}
        for key, var in self.arg_vars.items():
            if isinstance(var, tk.BooleanVar):
                self.result[key] = var.get()
            else:
                value = var.get().strip()
                if value:
                    self.result[key] = value
        
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel dialog"""
        self.dialog.destroy()

class UploadAssistantGUI:
    """Main application window"""
    
    def __init__(self):
        self.config = UAConfig()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("Upload Assistant Manager")
        self.root.geometry("1200x700")
        
        # Configure grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=2)
        
        self.create_widgets()
        self.create_menu()
        
        # Initial load
        self.on_filter_change(self.config.get('PATHS', 'torrents_dir'))
    
    def create_widgets(self):
        """Create main UI widgets"""
        # Left panel (filters and navigation)
        self.filter_panel = FilterPanel(self.root, self.config, self.on_filter_change)
        self.filter_panel.frame.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)
        
        # Right panel (file operations)
        self.file_panel = FilePanel(self.root, self.config)
        self.file_panel.frame.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=5, pady=(0, 5))
    
    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Refresh", command=self.refresh_all)
        file_menu.add_separator()
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh Files", command=self.file_panel.refresh_files)
        view_menu.add_command(label="Refresh Directory Tree", command=self.filter_panel.refresh_directory_tree)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
    
    def on_filter_change(self, selected_path: str):
        """Handle filter or directory changes"""
        show_missing = self.filter_panel.get_missing_torrents_filter()
        self.file_panel.update_files(selected_path, show_missing)
        self.status_var.set(f"Directory: {selected_path}")
    
    def refresh_all(self):
        """Refresh all panels"""
        self.filter_panel.refresh_directory_tree()
        self.file_panel.refresh_files()
        self.status_var.set("Refreshed")
    
    def show_settings(self):
        """Show settings dialog"""
        settings_dialog = SettingsDialog(self.root, self.config)
        if settings_dialog.result:
            # Refresh after settings change
            self.filter_panel.refresh_directory_tree()
            self.status_var.set("Settings updated")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
                          "Upload Assistant Manager v1.0\n\n"
                          "A Midnight Commander-style GUI for managing\n"
                          "upload-assistant operations and torrent files.\n\n"
                          "Features:\n"
                          "• Directory navigation and filtering\n"
                          "• Missing torrent detection\n" 
                          "• Upload Assistant integration\n"
                          "• File management operations")
    
    def run(self):
        """Start the application"""
        self.root.mainloop()

class SettingsDialog:
    """Settings configuration dialog"""
    
    def __init__(self, parent, config: UAConfig):
        self.config = config
        self.result = False
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.geometry("500x300")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (250)
        y = (self.dialog.winfo_screenheight() // 2) - (150)
        self.dialog.geometry(f"500x300+{x}+{y}")
        
        self.create_widgets()
    
    def create_widgets(self):
        """Create settings widgets"""
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill="both", expand=True)
        
        # Paths section
        paths_frame = ttk.LabelFrame(main_frame, text="Paths", padding=10)
        paths_frame.pack(fill="x", pady=(0, 10))
        
        # Logs directory
        ttk.Label(paths_frame, text="Logs Directory:").grid(row=0, column=0, sticky="w", pady=2)
        self.logs_var = tk.StringVar(value=self.config.get('PATHS', 'logs_dir'))
        logs_frame = ttk.Frame(paths_frame)
        logs_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=2)
        ttk.Entry(logs_frame, textvariable=self.logs_var).pack(side="left", fill="x", expand=True)
        ttk.Button(logs_frame, text="Browse", command=lambda: self.browse_directory(self.logs_var)).pack(side="right", padx=(5, 0))
        
        # Torrents directory  
        ttk.Label(paths_frame, text="Torrents Directory:").grid(row=1, column=0, sticky="w", pady=2)
        self.torrents_var = tk.StringVar(value=self.config.get('PATHS', 'torrents_dir'))
        torrents_frame = ttk.Frame(paths_frame)
        torrents_frame.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=2)
        ttk.Entry(torrents_frame, textvariable=self.torrents_var).pack(side="left", fill="x", expand=True)
        ttk.Button(torrents_frame, text="Browse", command=lambda: self.browse_directory(self.torrents_var)).pack(side="right", padx=(5, 0))
        
        # Upload Assistant path
        ttk.Label(paths_frame, text="Upload Assistant:").grid(row=2, column=0, sticky="w", pady=2)
        self.ua_var = tk.StringVar(value=self.config.get('PATHS', 'upload_assistant_path'))
        ua_frame = ttk.Frame(paths_frame)
        ua_frame.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=2)
        ttk.Entry(ua_frame, textvariable=self.ua_var).pack(side="left", fill="x", expand=True)
        ttk.Button(ua_frame, text="Browse", command=lambda: self.browse_file(self.ua_var)).pack(side="right", padx=(5, 0))
        
        paths_frame.grid_columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", side="bottom")
        
        ttk.Button(button_frame, text="Cancel", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Save", command=self.save).pack(side="right")
    
    def browse_directory(self, var: tk.StringVar):
        """Browse for directory"""
        directory = filedialog.askdirectory(initialdir=var.get())
        if directory:
            var.set(directory)
    
    def browse_file(self, var: tk.StringVar):
        """Browse for file"""
        file_path = filedialog.askopenfilename(initialdir=os.path.dirname(var.get()) if var.get() else "/")
        if file_path:
            var.set(file_path)
    
    def save(self):
        """Save settings"""
        self.config.set('PATHS', 'logs_dir', self.logs_var.get())
        self.config.set('PATHS', 'torrents_dir', self.torrents_var.get())
        self.config.set('PATHS', 'upload_assistant_path', self.ua_var.get())
        self.result = True
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel settings"""
        self.dialog.destroy()

def main():
    """Main entry point"""
    try:
        app = UploadAssistantGUI()
        app.run()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Error running application: {e}")

if __name__ == "__main__":
    main()