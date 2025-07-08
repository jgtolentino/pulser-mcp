# Desktop Application Assets

This directory should contain the following icon files for the desktop application:

## Required Icons:

### icon.png (512x512)
- Main application icon in PNG format
- Used for Linux AppImage and general display
- Should feature the MCP logo or a server/database icon

### icon.ico (256x256, multi-size)
- Windows application icon
- Should contain multiple sizes: 16x16, 32x32, 48x48, 256x256
- Can be generated from icon.png using online converters

### icon.icns (512x512, multi-size)
- macOS application icon
- Should contain multiple sizes for Retina and non-Retina displays
- Can be generated from icon.png using tools like `iconutil` on macOS

## Icon Design Suggestions:

The icon should represent:
- 🚀 Server/rocket symbol for MCP server
- 💾 Database symbol for SQLite
- 🔗 Connection symbol for integration
- Modern, clean design that fits system aesthetics

## Creating Icons:

You can create these icons using:
1. **Design tools**: Figma, Sketch, Photoshop, GIMP
2. **Icon generators**: 
   - https://www.iconfinder.com/
   - https://icon-icons.com/
   - https://www.flaticon.com/
3. **Conversion tools**:
   - PNG to ICO: https://convertio.co/png-ico/
   - PNG to ICNS: Use macOS `iconutil` or online converters

## Temporary Solution:

For now, the application will use system default icons. Replace these files with proper icons before distribution.
