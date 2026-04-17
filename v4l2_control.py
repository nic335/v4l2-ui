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
import configparser
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

    @staticmethod
    def get_formats_and_resolutions(device_path: str) -> List[Dict]:
        """Parse v4l2-ctl --list-formats-ext into a list of format dicts"""
        try:
            result = subprocess.run(['v4l2-ctl', '-d', device_path, '--list-formats-ext'],
                                    capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            return []

        formats = []
        current_fmt = None
        current_res = None

        for line in result.stdout.split('\n'):
            fmt_match = re.search(r"\[\d+\]: '([^']+)' \(([^)]+)\)", line)
            if fmt_match:
                current_fmt = {'pixel_format': fmt_match.group(1),
                               'description': fmt_match.group(2),
                               'resolutions': []}
                formats.append(current_fmt)
                current_res = None
                continue

            if current_fmt is None:
                continue

            size_match = re.search(r'Size:\s+\S+\s+(\d+x\d+)', line)
            if size_match:
                current_res = {'size': size_match.group(1), 'fps': []}
                current_fmt['resolutions'].append(current_res)
                continue

            if current_res is not None:
                fps_match = re.search(r'Interval:.*\(([\d.]+) fps\)', line)
                if fps_match:
                    current_res['fps'].append(fps_match.group(1))

        return formats

    @staticmethod
    def get_device_info(device_path: str) -> Dict[str, Any]:
        """Parse v4l2-ctl --info into a capabilities dict"""
        try:
            result = subprocess.run(['v4l2-ctl', '-d', device_path, '--info'],
                                    capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError:
            return {}

        info = {'driver': '', 'card': '', 'bus': '', 'version': '',
                'capabilities': [], 'device_caps': []}
        section = None

        for line in result.stdout.split('\n'):
            stripped = line.strip()
            if not stripped:
                continue
            if 'Driver name' in line:
                info['driver'] = stripped.split(':', 1)[-1].strip()
            elif 'Card type' in line:
                info['card'] = stripped.split(':', 1)[-1].strip()
            elif 'Bus info' in line:
                info['bus'] = stripped.split(':', 1)[-1].strip()
            elif 'Driver version' in line:
                info['version'] = stripped.split(':', 1)[-1].strip()
            elif re.match(r'Capabilities\s*:', line):
                section = 'capabilities'
            elif re.match(r'Device Caps\s*:', line):
                section = 'device_caps'
            elif section and stripped and not re.search(r'0x[0-9a-f]+', stripped):
                info[section].append(stripped)

        return info

    @staticmethod
    def get_device_aliases(device_path: str) -> Dict[str, List[str]]:
        """Return all path aliases for a device grouped by type.
        Returns {'by-video': ['/dev/videoN'], 'by-id': [...], 'by-path': [...]}
        """
        aliases: Dict[str, List[str]] = {'by-video': [], 'by-id': [], 'by-path': []}
        try:
            real = os.path.realpath(device_path)
        except Exception:
            real = device_path
        if os.path.exists(real):
            aliases['by-video'].append(real)
        for path_type, directory in [('by-id', '/dev/v4l/by-id'),
                                     ('by-path', '/dev/v4l/by-path')]:
            try:
                for name in sorted(os.listdir(directory)):
                    link = os.path.join(directory, name)
                    try:
                        if os.path.realpath(link) == real:
                            aliases[path_type].append(link)
                    except Exception:
                        pass
            except (FileNotFoundError, PermissionError):
                pass
        return aliases

    @staticmethod
    def build_device_map() -> List[Dict]:
        """Return a list of dicts, one per physical video device, with all path aliases.
        Each dict: {'real': '/dev/videoN', 'by-video': [...], 'by-id': [...], 'by-path': [...]}
        """
        devices = V4L2Parser.list_devices()
        result = []
        seen_real = set()
        for dev in devices:
            real = os.path.realpath(dev.path)
            if real in seen_real:
                continue
            seen_real.add(real)
            aliases = V4L2Parser.get_device_aliases(real)
            aliases['real'] = real
            result.append(aliases)
        return result


class CrowsnestConfig:
    """Parser and writer for crowsnest.conf"""

    SEARCH_PATHS = [
        '~/printer_data/config/crowsnest.conf',
        '~/klipper_config/crowsnest.conf',
        '~/crowsnest/crowsnest.conf',
        '/etc/crowsnest.conf',
    ]

    def __init__(self, path: str = None):
        self.path = path or self._find_config()
        self.raw_lines: List[str] = []
        self.sections: Dict[str, Dict[str, str]] = {}
        if self.path:
            self._load()

    def _find_config(self) -> Optional[str]:
        for p in self.SEARCH_PATHS:
            expanded = os.path.expanduser(p)
            if os.path.isfile(expanded):
                return expanded
        return None

    def _load(self):
        try:
            with open(self.path, 'r') as f:
                self.raw_lines = f.readlines()
        except IOError:
            return
        cfg = configparser.RawConfigParser(
            comment_prefixes=('#', ';'),
            inline_comment_prefixes=('#',),
            delimiters=(':',),
            strict=False
        )
        cfg.read(self.path)
        self.sections = {s: dict(cfg[s]) for s in cfg.sections()}

    def get_cam_sections(self) -> List[Tuple[str, Dict[str, str]]]:
        return [(s, d) for s, d in self.sections.items()
                if s.lower().startswith('cam')]

    def update_cam(self, section: str, key: str, value: str):
        """Update key in section, preserving file structure and comments."""
        in_section = False
        key_found = False
        commented_idx = -1
        next_section_idx = len(self.raw_lines)

        for i, line in enumerate(self.raw_lines):
            stripped = line.strip()
            sec_match = re.match(r'^\[(.+)\]', stripped)
            if sec_match:
                if in_section:
                    next_section_idx = i
                    break
                in_section = sec_match.group(1).strip().lower() == section.lower()
                continue
            if not in_section:
                continue

            active = re.match(r'^(' + re.escape(key) + r')\s*:', stripped, re.IGNORECASE)
            if active:
                trail = re.search(r'\s{2,}(#.*)$', line)
                comment = '  ' + trail.group(1) if trail else ''
                self.raw_lines[i] = f"{key}: {value}{comment}\n"
                key_found = True
                break

            if commented_idx < 0:
                commented = re.match(
                    r'^#+\s*(' + re.escape(key) + r')\s*:', stripped, re.IGNORECASE)
                if commented:
                    commented_idx = i

        if not key_found:
            if commented_idx >= 0:
                self.raw_lines[commented_idx] = f"{key}: {value}\n"
            else:
                self.raw_lines.insert(next_section_idx, f"{key}: {value}\n")

        if section not in self.sections:
            self.sections[section] = {}
        self.sections[section][key] = value

    def next_cam_name(self) -> str:
        """Return the next available [cam N] name"""
        existing = [s for s in self.sections if s.lower().startswith('cam')]
        nums = []
        for s in existing:
            m = re.search(r'(\d+)', s)
            if m:
                nums.append(int(m.group(1)))
        n = 1
        while n in nums:
            n += 1
        return f'cam {n}'

    def add_cam_section(self, section: str, defaults: Dict[str, str] = None) -> bool:
        """Append a new cam section to the file"""
        if section in self.sections:
            return False
        defaults = defaults or {
            'mode': 'ustreamer',
            'port': '8080',
            'device': '/dev/video0',
            'resolution': '1280x720',
            'max_fps': '30',
            'v4l2ctl': '',
        }
        lines = [f'\n[{section}]\n']
        for k, v in defaults.items():
            if v:
                lines.append(f'{k}: {v}\n')
        self.raw_lines.extend(lines)
        self.sections[section] = dict(defaults)
        return True

    def delete_cam_section(self, section: str) -> bool:
        """Remove a cam section and all its lines from the file"""
        if section not in self.sections:
            return False
        in_section = False
        start_idx = -1
        end_idx = len(self.raw_lines)
        for i, line in enumerate(self.raw_lines):
            m = re.match(r'^\[(.+)\]', line.strip())
            if m:
                if m.group(1).strip().lower() == section.lower():
                    in_section = True
                    start_idx = i
                elif in_section:
                    end_idx = i
                    break
        if start_idx < 0:
            return False
        # Also eat a blank line immediately before the section header
        while start_idx > 0 and self.raw_lines[start_idx - 1].strip() == '':
            start_idx -= 1
        del self.raw_lines[start_idx:end_idx]
        del self.sections[section]
        return True

    def save(self) -> bool:
        if not self.path:
            return False
        try:
            with open(self.path, 'w') as f:
                f.writelines(self.raw_lines)
            return True
        except IOError:
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
        self.device_info = {}
        self.formats = []
        
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
        
        self.device_info = V4L2Parser.get_device_info(self.current_device.path)
        self.formats = V4L2Parser.get_formats_and_resolutions(self.current_device.path)
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
            elif key == ord('i') or key == ord('I'):
                self.show_info_screen()
            elif key == ord('c') or key == ord('C'):
                self.show_crowsnest_editor()
            
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
        help_text = "[d] Device | [r] Refresh | [i] Info | [c] Crowsnest | [q] Quit"
        self.stdscr.addstr(0, width - len(help_text) - 1, help_text, curses.color_pair(5))
        self.stdscr.addstr(1, 0, "=" * (width - 1))
        
        crowsnest_config = self.generate_crowsnest_config()
        if len(crowsnest_config) > width - 1:
            crowsnest_config = crowsnest_config[:width-4] + "..."
        self.stdscr.addstr(height - 1, 0, crowsnest_config[:width-1], curses.color_pair(2))
        
        if self.status_message:
            self.stdscr.addstr(height - 2, 0, self.status_message[:width-1], curses.color_pair(3))
        
        nav_help = "↑↓: Navigate | ←→: Adjust | Enter: Edit | Space: Toggle | 0: Default | s: Save | l: Load | i: Info | c: Crowsnest"
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
    
    def show_info_screen(self):
        """Show device capabilities and available resolutions"""
        # Build the lines to display
        lines = []

        # Device info section
        if self.device_info:
            lines.append(('header', 'Device Information'))
            lines.append(('separator', ''))
            for key, label in [('driver', 'Driver'), ('card', 'Card'),
                                ('bus', 'Bus'), ('version', 'Version')]:
                val = self.device_info.get(key, '')
                if val:
                    lines.append(('field', f"  {label:<12}: {val}"))
            caps = self.device_info.get('capabilities', [])
            if caps:
                lines.append(('field', f"  {'Capabilities':<12}: {caps[0]}"))
                for cap in caps[1:]:
                    lines.append(('field', f"  {'':<14}  {cap}"))
            dev_caps = self.device_info.get('device_caps', [])
            if dev_caps:
                lines.append(('field', f"  {'Device Caps':<12}: {dev_caps[0]}"))
                for cap in dev_caps[1:]:
                    lines.append(('field', f"  {'':<14}  {cap}"))
        else:
            lines.append(('field', '  No device info available'))

        lines.append(('blank', ''))

        # Formats / resolutions section
        lines.append(('header', 'Supported Formats & Resolutions'))
        lines.append(('separator', ''))
        if self.formats:
            for fmt in self.formats:
                lines.append(('format', f"  [{fmt['pixel_format']}] {fmt['description']}"))
                for res in fmt['resolutions']:
                    fps_str = ', '.join(res['fps']) + ' fps' if res['fps'] else ''
                    lines.append(('resolution', f"      {res['size']:<16} {fps_str}"))
        else:
            lines.append(('field', '  No format info available'))

        # Scrollable display loop
        scroll = 0
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)

        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            visible = height - 3

            self.stdscr.addstr(0, 0, f"Camera Info: {self.current_device.name}", curses.A_BOLD)
            self.stdscr.addstr(1, 0, '=' * (width - 1))

            for row, (kind, text) in enumerate(lines[scroll:scroll + visible]):
                y = 2 + row
                if y >= height - 1:
                    break
                text = text[:width - 1]
                if kind == 'header':
                    self.stdscr.addstr(y, 0, text, curses.A_BOLD | curses.color_pair(2))
                elif kind == 'separator':
                    self.stdscr.addstr(y, 0, '─' * min(width - 1, 60), curses.color_pair(5))
                elif kind == 'format':
                    self.stdscr.addstr(y, 0, text, curses.color_pair(3))
                elif kind == 'resolution':
                    self.stdscr.addstr(y, 0, text, curses.color_pair(5))
                else:
                    self.stdscr.addstr(y, 0, text)

            footer = "↑↓/PgUp/PgDn: Scroll | q/Esc: Back"
            self.stdscr.addstr(height - 1, 0, footer[:width - 1], curses.color_pair(5))
            self.stdscr.refresh()

            key = self.stdscr.getch()
            max_scroll = max(0, len(lines) - visible)

            if key in (ord('q'), ord('Q'), 27):
                break
            elif key == curses.KEY_UP:
                scroll = max(0, scroll - 1)
            elif key == curses.KEY_DOWN:
                scroll = min(max_scroll, scroll + 1)
            elif key == curses.KEY_PPAGE:
                scroll = max(0, scroll - visible)
            elif key == curses.KEY_NPAGE:
                scroll = min(max_scroll, scroll + visible)

        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)

    def _text_input(self, prompt: str, default: str = '') -> str:
        """Inline text input, returns new value or default on cancel"""
        height, width = self.stdscr.getmaxyx()
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        curses.echo()
        curses.curs_set(1)
        self.stdscr.addstr(height - 1, 0, ' ' * (width - 1))
        self.stdscr.addstr(height - 1, 0, prompt[:width - 1])
        self.stdscr.refresh()
        try:
            raw = self.stdscr.getstr(height - 1, len(prompt), width - len(prompt) - 2)
            result = raw.decode('utf-8').strip()
        except (UnicodeDecodeError, Exception):
            result = ''
        curses.noecho()
        curses.curs_set(0)
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)
        return result if result else default

    def _show_popup(self, message: str):
        """Show a one-line message and wait for a keypress"""
        height, width = self.stdscr.getmaxyx()
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)
        self.stdscr.addstr(height - 1, 0, ' ' * (width - 1))
        self.stdscr.addstr(height - 1, 0, (message + '  [any key]')[:width - 1],
                           curses.color_pair(4))
        self.stdscr.refresh()
        self.stdscr.getch()
        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)

    def show_crowsnest_editor(self):
        """Crowsnest.conf camera section editor"""
        cfg = CrowsnestConfig()
        if not cfg.path:
            self._show_popup('crowsnest.conf not found')
            return

        while True:
            cfg._load()
            cam_sections = cfg.get_cam_sections()
            if not cam_sections:
                self._show_popup(f'No [cam N] sections found in {cfg.path}')
                return

            selected = 0
            result = self._crowsnest_section_picker(cfg, cam_sections, selected)
            if result is None:
                return
            selected, cam_sections = result
            section_name, section_data = cam_sections[selected]
            self._edit_crowsnest_cam(cfg, section_name, dict(section_data))

    def _confirm(self, message: str) -> bool:
        """Show a y/n confirmation on the bottom line, return True if confirmed"""
        height, width = self.stdscr.getmaxyx()
        prompt = f'{message}  [y/N]: '
        self.stdscr.addstr(height - 1, 0, ' ' * (width - 1))
        self.stdscr.addstr(height - 1, 0, prompt[:width - 1], curses.color_pair(4))
        self.stdscr.refresh()
        key = self.stdscr.getch()
        return key in (ord('y'), ord('Y'))

    def _crowsnest_section_picker(self, cfg: 'CrowsnestConfig',
                                   cam_sections, initial_sel: int):
        """Pick a cam section; returns (selected_idx, cam_sections) or None to exit"""
        selected = initial_sel
        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)

        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            self.stdscr.addstr(0, 0,
                f'Crowsnest Config: {cfg.path}', curses.A_BOLD)
            self.stdscr.addstr(1, 0, '=' * (width - 1))
            self.stdscr.addstr(3, 0, 'Select camera section to edit:',
                               curses.color_pair(2))

            for idx, (sec, data) in enumerate(cam_sections):
                y = 5 + idx
                if y >= height - 2:
                    break
                device = data.get('device', '?')
                res    = data.get('resolution', '?')
                fps    = data.get('max_fps', '?')
                v4l2   = data.get('v4l2ctl', '')
                summary = f"{device}  {res}@{fps}fps"
                if v4l2:
                    summary += f"  [{v4l2[:20]}{'...' if len(v4l2)>20 else ''}]"
                prefix = '> ' if idx == selected else '  '
                line = f"{prefix}{sec}: {summary}"
                attr = curses.color_pair(1) if idx == selected else 0
                self.stdscr.addstr(y, 0, line[:width - 1], attr)

            self.stdscr.addstr(height - 1, 0,
                '↑↓: Navigate | Enter: Edit | n: New cam | x: Delete | q: Back',
                curses.color_pair(5))
            self.stdscr.refresh()

            key = self.stdscr.getch()
            if key in (ord('q'), ord('Q'), 27):
                self.stdscr.nodelay(True)
                self.stdscr.timeout(50)
                return None

            elif key == curses.KEY_UP:
                selected = max(0, selected - 1)
            elif key == curses.KEY_DOWN:
                selected = min(len(cam_sections) - 1, selected + 1)

            elif key in (ord('\n'), curses.KEY_ENTER, 10):
                self.stdscr.nodelay(True)
                self.stdscr.timeout(50)
                return selected, cam_sections

            elif key in (ord('n'), ord('N')):
                # Determine next port from existing sections
                existing_ports = []
                for _, d in cam_sections:
                    try:
                        existing_ports.append(int(d.get('port', 0)))
                    except ValueError:
                        pass
                next_port = str(max(existing_ports) + 1) if existing_ports else '8080'

                new_name = cfg.next_cam_name()
                # Pre-fill device from first available v4l2 device
                all_devices = V4L2Parser.list_devices()
                default_device = all_devices[0].path if all_devices else '/dev/video0'
                formats = V4L2Parser.get_formats_and_resolutions(default_device)
                default_res = '1280x720'
                default_fps = '30'
                if formats and formats[0]['resolutions']:
                    r = formats[0]['resolutions'][0]
                    default_res = r['size']
                    default_fps = r['fps'][0] if r['fps'] else '30'

                cfg.add_cam_section(new_name, {
                    'mode':       'ustreamer',
                    'port':       next_port,
                    'device':     default_device,
                    'resolution': default_res,
                    'max_fps':    default_fps,
                    'v4l2ctl':    '',
                })
                if cfg.save():
                    cfg._load()
                    cam_sections = cfg.get_cam_sections()
                    # Jump selection to the new entry
                    selected = len(cam_sections) - 1
                    # Open editor immediately
                    self.stdscr.nodelay(True)
                    self.stdscr.timeout(50)
                    return selected, cam_sections

            elif key in (ord('x'), ord('X'), curses.KEY_DC):
                if cam_sections:
                    sec_name = cam_sections[selected][0]
                    if self._confirm(f"Delete [{sec_name}]?"):
                        cfg.delete_cam_section(sec_name)
                        if cfg.save():
                            cfg._load()
                            cam_sections = cfg.get_cam_sections()
                            selected = max(0, min(selected, len(cam_sections) - 1))
                            if not cam_sections:
                                self.stdscr.nodelay(True)
                                self.stdscr.timeout(50)
                                return None

    def _edit_crowsnest_cam(self, cfg: 'CrowsnestConfig',
                             section: str, data: Dict):
        """Edit a single cam section with live resolution/fps and path-type pickers"""
        PATH_TYPES = ['by-id', 'by-path', 'by-video']
        MODES = ['ustreamer', 'camera-streamer']

        # Build physical device map (one entry per real /dev/videoN)
        device_map = V4L2Parser.build_device_map()

        def _detect_path_type(path: str) -> str:
            if '/by-id/' in path:
                return 'by-id'
            if '/by-path/' in path:
                return 'by-path'
            return 'by-video'

        def _path_for(entry: Dict, ptype: str) -> str:
            paths = entry.get(ptype, [])
            if paths:
                return paths[0]
            bv = entry.get('by-video', [])
            return bv[0] if bv else entry.get('real', '/dev/video0')

        def _find_phys_idx(path: str) -> int:
            real = os.path.realpath(path)
            for i, e in enumerate(device_map):
                if e.get('real') == real:
                    return i
                for pt in ('by-id', 'by-path', 'by-video'):
                    if path in e.get(pt, []):
                        return i
            return 0

        current_path = data.get('device', '')
        path_type = _detect_path_type(current_path)
        phys_idx = _find_phys_idx(current_path) if device_map else 0

        fields = {
            'device':     current_path,
            'mode':       data.get('mode', 'ustreamer'),
            'port':       data.get('port', '8080'),
            'resolution': data.get('resolution', ''),
            'max_fps':    data.get('max_fps', '30'),
            'v4l2ctl':    data.get('v4l2ctl', ''),
        }

        # path_type is UI-only; not a real field key
        FIELD_LABELS = {
            'device':    'device',
            'path_type': 'path type',
            'mode':      'mode',
            'port':      'port',
            'resolution':'resolution',
            'max_fps':   'max_fps',
            'v4l2ctl':   'v4l2ctl',
        }
        field_order = ['device', 'path_type', 'mode', 'port',
                       'resolution', 'max_fps', 'v4l2ctl']
        selected_field = 0
        status = f'Editing [{section}]  —  w: Save  |  q: Cancel'

        # Load formats for the configured device
        formats = V4L2Parser.get_formats_and_resolutions(fields['device'])

        self.stdscr.nodelay(False)
        self.stdscr.timeout(-1)

        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            self.stdscr.addstr(0, 0,
                f'Edit [{section}]  ←  {cfg.path}', curses.A_BOLD)
            self.stdscr.addstr(1, 0, '=' * (width - 1))

            for row, fname in enumerate(field_order):
                y = 3 + row
                if y >= height - 3:
                    break
                sel = (row == selected_field)
                label = f"  {FIELD_LABELS[fname]:<12}"

                if fname == 'path_type':
                    # Show available types for current device
                    avail = []
                    if device_map and phys_idx < len(device_map):
                        e = device_map[phys_idx]
                        for pt in PATH_TYPES:
                            if e.get(pt):
                                avail.append(pt)
                    val = path_type
                    hint = f'  ({"/".join(avail)})  ◄/► cycle' if sel else ''
                else:
                    val = fields[fname]
                    hint = ''
                    if sel:
                        if fname in ('device', 'mode', 'resolution', 'max_fps'):
                            hint = '  ◄/► cycle'
                        elif fname == 'v4l2ctl':
                            hint = '  Enter: edit  |  a: auto-fill'
                        elif fname == 'port':
                            hint = '  Enter: edit'

                line = f"{label}: {val}{hint}"
                if sel:
                    self.stdscr.addstr(y, 0, line[:width - 1], curses.color_pair(1))
                else:
                    self.stdscr.addstr(y, 0, line[:width - 1])

            self.stdscr.addstr(height - 2, 0, status[:width - 1],
                               curses.color_pair(3))
            self.stdscr.addstr(height - 1, 0,
                '↑↓: Field | ◄►: Cycle | Enter: Edit | a: Auto v4l2ctl | w: Save | q: Cancel',
                curses.color_pair(5))
            self.stdscr.refresh()

            key = self.stdscr.getch()
            fname = field_order[selected_field]

            if key in (ord('q'), ord('Q'), 27):
                break

            elif key in (ord('w'), ord('W')):
                for k, v in fields.items():
                    cfg.update_cam(section, k, v)
                if cfg.save():
                    status = f'Saved [{section}] to {cfg.path}'
                else:
                    status = 'ERROR: could not write file'

            elif key == curses.KEY_UP:
                selected_field = max(0, selected_field - 1)
            elif key == curses.KEY_DOWN:
                selected_field = min(len(field_order) - 1, selected_field + 1)

            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                d = 1 if key == curses.KEY_RIGHT else -1

                if fname == 'device' and device_map:
                    phys_idx = (phys_idx + d) % len(device_map)
                    entry = device_map[phys_idx]
                    # Keep current path_type if available, else fallback
                    if not entry.get(path_type):
                        for pt in PATH_TYPES:
                            if entry.get(pt):
                                path_type = pt
                                break
                    fields['device'] = _path_for(entry, path_type)
                    formats = V4L2Parser.get_formats_and_resolutions(
                        fields['device'])
                    if formats and formats[0]['resolutions']:
                        r = formats[0]['resolutions'][0]
                        fields['resolution'] = r['size']
                        fields['max_fps'] = r['fps'][0] if r['fps'] else '30'

                elif fname == 'path_type' and device_map and phys_idx < len(device_map):
                    entry = device_map[phys_idx]
                    avail = [pt for pt in PATH_TYPES if entry.get(pt)]
                    if avail:
                        try:
                            idx = avail.index(path_type)
                        except ValueError:
                            idx = 0
                        path_type = avail[(idx + d) % len(avail)]
                        fields['device'] = _path_for(entry, path_type)

                elif fname == 'mode':
                    idx = MODES.index(fields['mode']) if fields['mode'] in MODES else 0
                    fields['mode'] = MODES[(idx + d) % len(MODES)]

                elif fname == 'resolution':
                    res_list = []
                    for fmt in formats:
                        for r in fmt['resolutions']:
                            if r['size'] not in res_list:
                                res_list.append(r['size'])
                    if res_list:
                        try:
                            idx = res_list.index(fields['resolution'])
                        except ValueError:
                            idx = 0
                        idx = (idx + d) % len(res_list)
                        fields['resolution'] = res_list[idx]
                        for fmt in formats:
                            for r in fmt['resolutions']:
                                if r['size'] == fields['resolution'] and r['fps']:
                                    fields['max_fps'] = r['fps'][0]
                                    break

                elif fname == 'max_fps':
                    fps_set: List[str] = []
                    for fmt in formats:
                        for r in fmt['resolutions']:
                            if r['size'] == fields['resolution']:
                                for f in r['fps']:
                                    if f not in fps_set:
                                        fps_set.append(f)
                    if fps_set:
                        try:
                            idx = fps_set.index(fields['max_fps'])
                        except ValueError:
                            idx = 0
                        fields['max_fps'] = fps_set[(idx + d) % len(fps_set)]

            elif key in (ord('\n'), curses.KEY_ENTER, 10):
                if fname in ('port', 'v4l2ctl', 'resolution', 'max_fps'):
                    fields[fname] = self._text_input(
                        f'Enter {fname}: ', fields[fname])
                elif fname == 'device':
                    new_path = self._text_input('Enter device path: ', fields['device'])
                    fields['device'] = new_path
                    path_type = _detect_path_type(new_path)
                    phys_idx = _find_phys_idx(new_path)
                    formats = V4L2Parser.get_formats_and_resolutions(new_path)

            elif key in (ord('a'), ord('A')):
                if self.controls and self.current_device:
                    parts = []
                    for ctrl in self.controls:
                        if ctrl.inactive:
                            continue
                        if ctrl.ctrl_type == 'int' and ctrl.value != ctrl.default:
                            parts.append(f'{ctrl.name}={ctrl.value}')
                        elif ctrl.ctrl_type == 'bool' and ctrl.value != ctrl.default:
                            parts.append(f'{ctrl.name}={ctrl.value}')
                        elif ctrl.ctrl_type == 'menu' and ctrl.current_menu_idx != ctrl.default:
                            parts.append(f'{ctrl.name}={ctrl.current_menu_idx}')
                    fields['v4l2ctl'] = ','.join(parts)
                    status = (f'Auto-filled v4l2ctl from '
                              f'{self.current_device.path} '
                              f'({len(parts)} non-default values)')
                else:
                    status = 'No controls loaded for current device'

        self.stdscr.nodelay(True)
        self.stdscr.timeout(50)

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
