#!/usr/bin/env python3
"""
V4L2 Control UI - Interactive terminal interface for v4l2-ctl camera controls
"""

import subprocess
import re
import curses
import sys
import json
import os
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import time


class V4L2Device:
    """Represents a V4L2 video device"""
    def __init__(self, path: str, name: str):
        self.path = path
        self.name = name
    
    def __str__(self):
        return f"{self.path} - {self.name}"


class V4L2Control:
    """Represents a V4L2 control parameter"""
    def __init__(self, name: str, ctrl_type: str, min_val: int = 0, max_val: int = 0, 
                 step: int = 1, default: Any = 0, value: Any = 0, 
                 menu_options: List[str] = None, inactive: bool = False, 
                 menu_indices: List[int] = None, current_menu_idx: int = 0):
        self.name = name
        self.ctrl_type = ctrl_type  # 'int', 'bool', 'menu'
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        self.default = default
        self.value = value
        self.menu_options = menu_options or []
        self.menu_indices = menu_indices or []  # Actual v4l2 indices for menu items
        self.current_menu_idx = current_menu_idx  # Current v4l2 index value
        self.inactive = inactive
    
    def format_value(self) -> str:
        """Format the current value for display"""
        if self.ctrl_type == 'bool':
            return 'ON' if self.value else 'OFF'
        elif self.ctrl_type == 'menu':
            return str(self.value)
        else:
            return str(self.value)
    
    def format_range(self) -> str:
        """Format the range/type info for display"""
        if self.ctrl_type == 'bool':
            return '[toggle]'
        elif self.ctrl_type == 'menu':
            return '[menu]'
        else:
            return f'[{self.min_val}-{self.max_val}, step {self.step}]'
    
    def get_slider_position(self, width: int = 15) -> int:
        """Get slider position for integer controls"""
        if self.ctrl_type != 'int' or self.max_val == self.min_val:
            return 0
        ratio = (self.value - self.min_val) / (self.max_val - self.min_val)
        return int(ratio * width)
    
    def render_visual(self, width: int = 15) -> str:
        """Render visual indicator for the control"""
        if self.ctrl_type == 'bool':
            checked = '[●]' if self.value else '[ ]'
            return f"{checked} ON  {'[ ]' if self.value else '[●]'} OFF"
        elif self.ctrl_type == 'menu':
            return f"[{' | '.join(self.menu_options)}]"
        else:
            pos = self.get_slider_position(width)
            slider = '─' * pos + '●' + '─' * (width - pos)
            return f'◄{slider}►'


class V4L2Parser:
    """Parser for v4l2-ctl command outputs"""
    
    @staticmethod
    def list_devices() -> List[V4L2Device]:
        """Parse v4l2-ctl --list-devices output"""
        try:
            result = subprocess.run(['v4l2-ctl', '--list-devices'], 
                                  capture_output=True, text=True, check=True)
            devices = []
            current_name = None
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if not line:
                    continue
                
                if line.startswith('/dev/video'):
                    if current_name:
                        devices.append(V4L2Device(line, current_name))
                elif not line.startswith('/dev/'):
                    current_name = line.rstrip(':')
            
            return devices
        except subprocess.CalledProcessError:
            return []
    
    @staticmethod
    def parse_control_line(line: str) -> Optional[V4L2Control]:
        """Parse a single control line from v4l2-ctl --list-ctrls"""
        line = line.strip()
        if not line or line.endswith('Controls'):
            return None
        
        int_pattern = r'(\w+)\s+0x[0-9a-f]+\s+\(int\)\s+:\s+min=(-?\d+)\s+max=(-?\d+)\s+step=(\d+)\s+default=(-?\d+)\s+value=(-?\d+)'
        bool_pattern = r'(\w+)\s+0x[0-9a-f]+\s+\(bool\)\s+:\s+default=(\d+)\s+value=(\d+)'
        menu_pattern = r'(\w+)\s+0x[0-9a-f]+\s+\(menu\)\s+:\s+min=(\d+)\s+max=(\d+)\s+default=(\d+)\s+value=(\d+)\s+\(([^)]+)\)'
        
        inactive = 'flags=inactive' in line
        
        int_match = re.search(int_pattern, line)
        if int_match:
            name, min_v, max_v, step, default, value = int_match.groups()
            return V4L2Control(name, 'int', int(min_v), int(max_v), int(step), 
                             int(default), int(value), inactive=inactive)
        
        bool_match = re.search(bool_pattern, line)
        if bool_match:
            name, default, value = bool_match.groups()
            return V4L2Control(name, 'bool', default=int(default), 
                             value=int(value), inactive=inactive)
        
        menu_match = re.search(menu_pattern, line)
        if menu_match:
            name, min_v, max_v, default, value_idx, current_option = menu_match.groups()
            return V4L2Control(name, 'menu', int(min_v), int(max_v), 1,
                             int(default), current_option, inactive=inactive,
                             current_menu_idx=int(value_idx))
        
        return None
    
    @staticmethod
    def list_controls(device_path: str) -> Tuple[List[V4L2Control], Dict[str, List[V4L2Control]]]:
        """Parse v4l2-ctl --list-ctrls output, grouped by category"""
        try:
            result = subprocess.run(['v4l2-ctl', '-d', device_path, '--list-ctrls'],
                                  capture_output=True, text=True, check=True)
            
            controls = []
            grouped = {}
            current_category = 'Controls'
            
            for line in result.stdout.split('\n'):
                if line.strip().endswith('Controls'):
                    current_category = line.strip()
                    grouped[current_category] = []
                    continue
                
                ctrl = V4L2Parser.parse_control_line(line)
                if ctrl:
                    controls.append(ctrl)
                    if current_category not in grouped:
                        grouped[current_category] = []
                    grouped[current_category].append(ctrl)
            
            return controls, grouped
        except subprocess.CalledProcessError:
            return [], {}
    
    @staticmethod
    def get_menu_options(device_path: str, control_name: str) -> Tuple[List[int], List[str]]:
        """Get menu options for a menu-type control, returns (indices, option_names)"""
        try:
            result = subprocess.run(['v4l2-ctl', '-d', device_path, '--list-ctrls-menus'],
                                  capture_output=True, text=True, check=True)
            
            in_menu = False
            indices = []
            options = []
            
            for line in result.stdout.split('\n'):
                if control_name in line and '(menu)' in line:
                    in_menu = True
                    continue
                
                if in_menu:
                    if line.strip() and line.startswith('\t'):
                        option_match = re.search(r'(\d+):\s+(.+)', line)
                        if option_match:
                            indices.append(int(option_match.group(1)))
                            options.append(option_match.group(2))
                    elif line.strip() and not line.startswith('\t'):
                        break
            
            return indices, options
        except subprocess.CalledProcessError:
            return [], []
    
    @staticmethod
    def set_control(device_path: str, control_name: str, value: Any) -> bool:
        """Set a control value"""
        try:
            subprocess.run(['v4l2-ctl', '-d', device_path, 
                          f'--set-ctrl={control_name}={value}'],
                         capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False


class V4L2UI:
    """Curses-based UI for V4L2 control"""
    
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.devices = []
        self.current_device = None
        self.controls = []
        self.grouped_controls = {}
        self.selected_idx = 0
        self.scroll_offset = 0
        self.status_message = ""
        self.preset_dir = os.path.expanduser("~/.config/v4l2-ui/presets")
        os.makedirs(self.preset_dir, exist_ok=True)
        
        # Progressive increment tracking
        self.last_key = None
        self.key_repeat_count = 0
        self.last_key_time = 0
        
        curses.curs_set(0)
        curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_CYAN, curses.COLOR_BLACK)
    
    def run(self):
        """Main UI loop"""
        self.devices = V4L2Parser.list_devices()
        
        if not self.devices:
            self.show_error("No V4L2 devices found!")
            return
        
        if not self.select_device():
            return
        
        self.control_loop()
    
    def select_device(self) -> bool:
        """Device selection menu"""
        selected = 0
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(0, 0, "V4L2 Control UI - Device Selection", curses.A_BOLD)
            self.stdscr.addstr(1, 0, "=" * min(width - 1, 50))
            
            self.stdscr.addstr(3, 0, "Available Video Devices:")
            
            for idx, device in enumerate(self.devices):
                y = 5 + idx
                if y >= height - 3:
                    break
                
                prefix = "> " if idx == selected else "  "
                display = f"{prefix}{idx + 1}. {device}"
                
                if idx == selected:
                    self.stdscr.addstr(y, 0, display[:width-1], curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, 0, display[:width-1])
            
            self.stdscr.addstr(height - 2, 0, "↑↓: Navigate | Enter: Select | q: Quit")
            
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            
            if key == ord('q') or key == ord('Q'):
                return False
            elif key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(self.devices) - 1:
                selected += 1
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                self.current_device = self.devices[selected]
                self.load_controls()
                return True
    
    def load_controls(self):
        """Load controls for the current device"""
        if not self.current_device:
            return
        
        self.controls, self.grouped_controls = V4L2Parser.list_controls(self.current_device.path)
        
        for ctrl in self.controls:
            if ctrl.ctrl_type == 'menu':
                indices, options = V4L2Parser.get_menu_options(self.current_device.path, ctrl.name)
                if options:
                    ctrl.menu_options = options
                    ctrl.menu_indices = indices
        
        self.selected_idx = 0
        self.scroll_offset = 0
        self.status_message = f"Loaded {len(self.controls)} controls"
    
    def control_loop(self):
        """Main control adjustment loop"""
        # Set nodelay mode for key repeat detection
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)  # 50ms timeout for getch
        
        # Draw initial screen
        self.draw_control_screen()
        
        while True:
            key = self.stdscr.getch()
            
            # Skip redraw if no key pressed (timeout) - prevents flickering
            if key == -1:
                continue
            
            # Track key repeats for progressive increment
            current_time = time.time()
            if key == self.last_key and key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                if current_time - self.last_key_time < 0.2:  # Within 200ms
                    self.key_repeat_count += 1
                else:
                    self.key_repeat_count = 1  # Reset to 1 (first press)
            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                self.key_repeat_count = 1  # First press of arrow key
            else:
                self.key_repeat_count = 0  # Different key pressed
            
            self.last_key = key
            self.last_key_time = current_time
            
            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('d') or key == ord('D'):
                if self.select_device():
                    self.draw_control_screen()
                    continue
                else:
                    break
            elif key == ord('r') or key == ord('R'):
                self.load_controls()
            elif key == curses.KEY_UP:
                self.move_selection(-1)
            elif key == curses.KEY_DOWN:
                self.move_selection(1)
            elif key == curses.KEY_LEFT:
                self.adjust_value_progressive(-1)
            elif key == curses.KEY_RIGHT:
                self.adjust_value_progressive(1)
            elif key == ord(' '):
                self.toggle_bool()
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                self.edit_value()
            elif key == ord('0'):
                self.reset_to_default()
            elif key == ord('s') or key == ord('S'):
                self.save_preset()
            elif key == ord('l') or key == ord('L'):
                self.load_preset()
            
            # Only redraw after processing a key
            self.draw_control_screen()
    
    def generate_crowsnest_config(self) -> str:
        """Generate crowsnest v4l2ctl configuration line (only non-default values)"""
        config_parts = []
        
        for ctrl in self.controls:
            if ctrl.inactive:
                continue
            
            # Only include controls that differ from default
            if ctrl.ctrl_type == 'int':
                if ctrl.value != ctrl.default:
                    config_parts.append(f"{ctrl.name}={ctrl.value}")
            elif ctrl.ctrl_type == 'bool':
                if ctrl.value != ctrl.default:
                    config_parts.append(f"{ctrl.name}={ctrl.value}")
            elif ctrl.ctrl_type == 'menu':
                if ctrl.current_menu_idx != ctrl.default:
                    config_parts.append(f"{ctrl.name}={ctrl.current_menu_idx}")
        
        if not config_parts:
            return "v4l2ctl: (all defaults)"
        
        return f"v4l2ctl: {','.join(config_parts)}"
    
    def draw_control_screen(self):
        """Draw the main control screen"""
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        self.stdscr.addstr(0, 0, f"Device: {self.current_device}", curses.A_BOLD)
        help_text = "[d] Change Device | [r] Refresh | [q] Quit"
        self.stdscr.addstr(0, width - len(help_text) - 1, help_text, curses.color_pair(5))
        self.stdscr.addstr(1, 0, "=" * (width - 1))
        
        crowsnest_config = self.generate_crowsnest_config()
        if len(crowsnest_config) > width - 1:
            crowsnest_config = crowsnest_config[:width-4] + "..."
        self.stdscr.addstr(height - 1, 0, crowsnest_config[:width-1], curses.color_pair(2))
        
        if self.status_message:
            self.stdscr.addstr(height - 2, 0, self.status_message[:width-1], curses.color_pair(3))
        
        nav_help = "↑↓: Navigate | ←→: Adjust | Enter: Edit | Space: Toggle | 0: Default | s: Save | l: Load"
        self.stdscr.addstr(height - 3, 0, nav_help[:width-1], curses.color_pair(5))
        
        visible_height = height - 6
        
        if self.selected_idx < self.scroll_offset:
            self.scroll_offset = self.selected_idx
        elif self.selected_idx >= self.scroll_offset + visible_height:
            self.scroll_offset = self.selected_idx - visible_height + 1
        
        y = 3
        current_category = None
        flat_idx = 0
        
        for category, ctrls in self.grouped_controls.items():
            if y >= height - 4:
                break
            
            if flat_idx > self.scroll_offset + visible_height:
                break
            
            if flat_idx >= self.scroll_offset:
                self.stdscr.addstr(y, 0, category, curses.A_BOLD | curses.color_pair(2))
                y += 1
            flat_idx += 1
            
            for ctrl in ctrls:
                if y >= height - 4:
                    break
                
                if flat_idx > self.scroll_offset + visible_height:
                    break
                
                if flat_idx >= self.scroll_offset:
                    self.draw_control_line(y, ctrl, flat_idx == self.selected_idx, width)
                    y += 1
                
                flat_idx += 1
        
        self.stdscr.refresh()
    
    def draw_control_line(self, y: int, ctrl: V4L2Control, selected: bool, width: int):
        """Draw a single control line"""
        prefix = "> " if selected else "  "
        
        name_width = 30
        value_width = 10
        range_width = 20
        
        name_str = f"{prefix}{ctrl.name:<{name_width}}"[:name_width + 2]
        value_str = f"{ctrl.format_value():>{value_width}}"[:value_width]
        range_str = f"{ctrl.format_range():<{range_width}}"[:range_width]
        visual_str = ctrl.render_visual(15)
        
        inactive_suffix = " (inactive)" if ctrl.inactive else ""
        
        line = f"{name_str} {value_str}  {range_str}  {visual_str}{inactive_suffix}"
        
        if selected:
            self.stdscr.addstr(y, 0, line[:width-1], curses.color_pair(1))
        elif ctrl.inactive:
            self.stdscr.addstr(y, 0, line[:width-1], curses.color_pair(4))
        else:
            self.stdscr.addstr(y, 0, line[:width-1])
    
    def move_selection(self, delta: int):
        """Move selection up or down"""
        total_items = sum(len(ctrls) + 1 for ctrls in self.grouped_controls.values())
        self.selected_idx = max(0, min(total_items - 1, self.selected_idx + delta))
    
    def get_selected_control(self) -> Optional[V4L2Control]:
        """Get the currently selected control"""
        flat_idx = 0
        for category, ctrls in self.grouped_controls.items():
            flat_idx += 1
            for ctrl in ctrls:
                if flat_idx == self.selected_idx:
                    return ctrl
                flat_idx += 1
        return None
    
    def adjust_value_progressive(self, delta: int):
        """Adjust value with progressive increment based on key hold duration"""
        ctrl = self.get_selected_control()
        if not ctrl or ctrl.inactive:
            return
        
        # Determine multiplier based on repeat count
        # 1-8 repeats: x1, 9-20 repeats: x10, 21+ repeats: x100
        if self.key_repeat_count <= 8:
            multiplier = 1
        elif self.key_repeat_count <= 40:
            multiplier = 10
        else:
            multiplier = 50
        
        if ctrl.ctrl_type == 'int':
            # Calculate step with multiplier
            step_size = ctrl.step * multiplier
            new_value = ctrl.value + (delta * step_size)
            new_value = max(ctrl.min_val, min(ctrl.max_val, new_value))
            
            if V4L2Parser.set_control(self.current_device.path, ctrl.name, new_value):
                ctrl.value = new_value
                if multiplier > 1:
                    self.status_message = f"Set {ctrl.name} = {new_value} (x{multiplier})"
                else:
                    self.status_message = f"Set {ctrl.name} = {new_value}"
            else:
                self.status_message = f"Failed to set {ctrl.name}"
        
        elif ctrl.ctrl_type == 'menu' and ctrl.menu_options and ctrl.menu_indices:
            try:
                current_pos = ctrl.menu_indices.index(ctrl.current_menu_idx)
                new_pos = (current_pos + delta) % len(ctrl.menu_indices)
                new_idx = ctrl.menu_indices[new_pos]
                new_value = ctrl.menu_options[new_pos]
                
                if V4L2Parser.set_control(self.current_device.path, ctrl.name, new_idx):
                    ctrl.current_menu_idx = new_idx
                    ctrl.value = new_value
                    self.status_message = f"Set {ctrl.name} = {new_value}"
                    # Refresh control states as this may affect other controls
                    self.refresh_control_states()
                else:
                    self.status_message = f"Failed to set {ctrl.name}"
            except (ValueError, IndexError) as e:
                self.status_message = f"Error adjusting {ctrl.name}: {e}"
    
    def adjust_value(self, delta: int):
        """Adjust the value of the selected control (legacy method)"""
        # Reset repeat count for non-progressive calls
        self.key_repeat_count = 0
        self.adjust_value_progressive(delta)
    
    def toggle_bool(self):
        """Toggle a boolean control"""
        ctrl = self.get_selected_control()
        if not ctrl or ctrl.ctrl_type != 'bool' or ctrl.inactive:
            return
        
        new_value = 0 if ctrl.value else 1
        
        if V4L2Parser.set_control(self.current_device.path, ctrl.name, new_value):
            ctrl.value = new_value
            self.status_message = f"Set {ctrl.name} = {'ON' if new_value else 'OFF'}"
            # Refresh control states as this may affect other controls
            self.refresh_control_states()
        else:
            self.status_message = f"Failed to set {ctrl.name}"
    
    def edit_value(self):
        """Edit value directly via text input"""
        ctrl = self.get_selected_control()
        if not ctrl or ctrl.ctrl_type != 'int' or ctrl.inactive:
            return
        
        height, width = self.stdscr.getmaxyx()
        
        # Restore blocking mode for text input
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        
        curses.echo()
        curses.curs_set(1)
        
        prompt = f"Enter value for {ctrl.name} ({ctrl.min_val}-{ctrl.max_val}): "
        self.stdscr.addstr(height - 1, 0, " " * (width - 1))
        self.stdscr.addstr(height - 1, 0, prompt)
        self.stdscr.refresh()
        
        try:
            input_str = self.stdscr.getstr(height - 1, len(prompt), 10).decode('utf-8')
            new_value = int(input_str)
            new_value = max(ctrl.min_val, min(ctrl.max_val, new_value))
            
            if V4L2Parser.set_control(self.current_device.path, ctrl.name, new_value):
                ctrl.value = new_value
                self.status_message = f"Set {ctrl.name} = {new_value}"
            else:
                self.status_message = f"Failed to set {ctrl.name}"
        except (ValueError, UnicodeDecodeError):
            self.status_message = "Invalid input"
        
        curses.noecho()
        curses.curs_set(0)
        
        # Restore nodelay mode for progressive increment
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
    
    def refresh_control_states(self):
        """Refresh the inactive state of all controls by re-parsing from v4l2-ctl"""
        try:
            result = subprocess.run(['v4l2-ctl', '-d', self.current_device.path, '--list-ctrls'],
                                  capture_output=True, text=True, check=True)
            
            # Parse inactive flags from output
            for line in result.stdout.split('\n'):
                for ctrl in self.controls:
                    if ctrl.name in line:
                        ctrl.inactive = 'flags=inactive' in line
                        break
        except subprocess.CalledProcessError:
            pass
    
    def reset_to_default(self):
        """Reset selected control to its default value"""
        ctrl = self.get_selected_control()
        if not ctrl or ctrl.inactive:
            return
        
        if ctrl.ctrl_type == 'int':
            if V4L2Parser.set_control(self.current_device.path, ctrl.name, ctrl.default):
                ctrl.value = ctrl.default
                self.status_message = f"Reset {ctrl.name} to default: {ctrl.default}"
            else:
                self.status_message = f"Failed to reset {ctrl.name}"
        
        elif ctrl.ctrl_type == 'bool':
            if V4L2Parser.set_control(self.current_device.path, ctrl.name, ctrl.default):
                ctrl.value = ctrl.default
                self.status_message = f"Reset {ctrl.name} to default: {'ON' if ctrl.default else 'OFF'}"
            else:
                self.status_message = f"Failed to reset {ctrl.name}"
        
        elif ctrl.ctrl_type == 'menu' and ctrl.menu_indices:
            try:
                pos = ctrl.menu_indices.index(ctrl.default)
                default_name = ctrl.menu_options[pos]
                if V4L2Parser.set_control(self.current_device.path, ctrl.name, ctrl.default):
                    ctrl.current_menu_idx = ctrl.default
                    ctrl.value = default_name
                    self.status_message = f"Reset {ctrl.name} to default: {default_name}"
                else:
                    self.status_message = f"Failed to reset {ctrl.name}"
            except (ValueError, IndexError):
                self.status_message = f"Cannot reset {ctrl.name}"
    
    def save_preset(self):
        """Save current control values to a preset file"""
        height, width = self.stdscr.getmaxyx()
        
        # Restore blocking mode for text input
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        
        curses.echo()
        curses.curs_set(1)
        
        prompt = "Preset name: "
        self.stdscr.addstr(height - 1, 0, " " * (width - 1))
        self.stdscr.addstr(height - 1, 0, prompt)
        self.stdscr.refresh()
        
        try:
            preset_name = self.stdscr.getstr(height - 1, len(prompt), 30).decode('utf-8').strip()
            
            if not preset_name:
                self.status_message = "Preset save cancelled"
                curses.noecho()
                curses.curs_set(0)
                return
            
            preset_data = {
                'device': self.current_device.path,
                'device_name': self.current_device.name,
                'timestamp': datetime.now().isoformat(),
                'controls': {}
            }
            
            for ctrl in self.controls:
                if ctrl.inactive:
                    continue
                
                if ctrl.ctrl_type == 'int':
                    preset_data['controls'][ctrl.name] = {'type': 'int', 'value': ctrl.value}
                elif ctrl.ctrl_type == 'bool':
                    preset_data['controls'][ctrl.name] = {'type': 'bool', 'value': ctrl.value}
                elif ctrl.ctrl_type == 'menu':
                    preset_data['controls'][ctrl.name] = {
                        'type': 'menu',
                        'value': ctrl.current_menu_idx,
                        'value_name': ctrl.value
                    }
            
            preset_file = os.path.join(self.preset_dir, f"{preset_name}.json")
            with open(preset_file, 'w') as f:
                json.dump(preset_data, f, indent=2)
            
            self.status_message = f"Saved preset: {preset_name}"
        
        except (UnicodeDecodeError, IOError) as e:
            self.status_message = f"Error saving preset: {e}"
        
        curses.noecho()
        curses.curs_set(0)
        
        # Restore nodelay mode for progressive increment
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
    
    def load_preset(self):
        """Load control values from a preset file"""
        preset_files = []
        try:
            for f in os.listdir(self.preset_dir):
                if f.endswith('.json'):
                    preset_files.append(f[:-5])  # Remove .json extension
        except OSError:
            self.status_message = "No presets found"
            return
        
        if not preset_files:
            self.status_message = "No presets found"
            return
        
        selected = 0
        
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            
            self.stdscr.addstr(0, 0, "Load Preset", curses.A_BOLD)
            self.stdscr.addstr(1, 0, "=" * min(width - 1, 50))
            
            self.stdscr.addstr(3, 0, "Available Presets:")
            
            for idx, preset in enumerate(preset_files):
                y = 5 + idx
                if y >= height - 3:
                    break
                
                prefix = " > " if idx == selected else "   "
                display = f"{prefix}{preset}"
                
                if idx == selected:
                    self.stdscr.addstr(y, 0, display[:width-1], curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, 0, display[:width-1])
            
            self.stdscr.addstr(height - 2, 0, "↑↓: Navigate | Enter: Load | Esc/q: Cancel")
            
            self.stdscr.refresh()
            
            key = self.stdscr.getch()
            
            if key == ord('q') or key == ord('Q') or key == 27:  # ESC
                self.status_message = "Load cancelled"
                return
            elif key == curses.KEY_UP and selected > 0:
                selected -= 1
            elif key == curses.KEY_DOWN and selected < len(preset_files) - 1:
                selected += 1
            elif key == ord('\n') or key == curses.KEY_ENTER or key == 10:
                preset_name = preset_files[selected]
                self.apply_preset(preset_name)
                return
    
    def apply_preset(self, preset_name: str):
        """Apply a preset to current controls"""
        preset_file = os.path.join(self.preset_dir, f"{preset_name}.json")
        
        try:
            with open(preset_file, 'r') as f:
                preset_data = json.load(f)
            
            applied_count = 0
            failed_count = 0
            
            for ctrl in self.controls:
                if ctrl.name in preset_data['controls']:
                    preset_ctrl = preset_data['controls'][ctrl.name]
                    
                    if ctrl.ctrl_type == preset_ctrl['type']:
                        value = preset_ctrl['value']
                        
                        if V4L2Parser.set_control(self.current_device.path, ctrl.name, value):
                            if ctrl.ctrl_type == 'int':
                                ctrl.value = value
                            elif ctrl.ctrl_type == 'bool':
                                ctrl.value = value
                            elif ctrl.ctrl_type == 'menu':
                                ctrl.current_menu_idx = value
                                if 'value_name' in preset_ctrl:
                                    ctrl.value = preset_ctrl['value_name']
                            applied_count += 1
                        else:
                            failed_count += 1
            
            self.status_message = f"Loaded preset '{preset_name}': {applied_count} applied, {failed_count} failed"
        
        except (IOError, json.JSONDecodeError, KeyError) as e:
            self.status_message = f"Error loading preset: {e}"
    
    def show_error(self, message: str):
        """Show an error message and wait for key press"""
        self.stdscr.clear()
        self.stdscr.addstr(0, 0, "Error", curses.A_BOLD | curses.color_pair(4))
        self.stdscr.addstr(2, 0, message)
        self.stdscr.addstr(4, 0, "Press any key to exit...")
        self.stdscr.refresh()
        self.stdscr.getch()


def main():
    """Main entry point"""
    try:
        curses.wrapper(lambda stdscr: V4L2UI(stdscr).run())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
