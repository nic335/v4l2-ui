# Contributing to V4L2 Control UI

Thanks for your interest in contributing! This project welcomes contributions from everyone.

## How to Contribute

### Reporting Bugs

If you find a bug, please open an issue with:
- Description of the problem
- Steps to reproduce
- Expected vs actual behavior
- Your system info (OS, Python version, camera model)
- Terminal output or error messages

### Suggesting Features

Have an idea? Open an issue describing:
- What you'd like to see
- Why it would be useful
- How it might work

### Submitting Pull Requests

We welcome PRs! Here's how:

1. **Fork the repository**
   ```bash
   # Click "Fork" on GitHub, then:
   git clone https://github.com/YOUR-USERNAME/v4l2-ui.git
   cd v4l2-ui
   ```

2. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

3. **Make your changes**
   - Keep changes focused and atomic
   - Follow existing code style
   - Test your changes thoroughly
   - Update documentation if needed

4. **Test it**
   ```bash
   # Make sure it runs without errors
   python3 -m py_compile v4l2_control.py
   ./v4l2-ui
   ```

5. **Commit your changes**
   ```bash
   git add .
   git commit -m "Brief description of your changes"
   ```

6. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   # Then open a Pull Request on GitHub
   ```

### Code Style

- Follow PEP 8 for Python code
- Use descriptive variable names
- Add comments for complex logic
- Keep functions focused and readable

### What We're Looking For

- Bug fixes
- New control types support
- UI improvements
- Performance optimizations
- Documentation improvements
- Better error handling
- Terminal compatibility fixes
- New features (discuss in an issue first!)

### Testing

Before submitting:
- Test on your camera/device
- Check that all existing features still work
- Verify it works over SSH/PuTTY
- Test with different terminal sizes

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/v4l2-ui.git
cd v4l2-ui

# Make it executable
chmod +x v4l2-ui v4l2_control.py

# Run it
./v4l2-ui
```

## Questions?

Open an issue or start a discussion. We're happy to help!

## Code of Conduct

Be respectful, constructive, and helpful. We're all here to make this tool better.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
