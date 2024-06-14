from PIL import ImageGrab

# Capture the entire screen
screenshot = ImageGrab.grab()

# Save the screenshot to a file
screenshot.save("screenshot.png")

# Close the screenshot
screenshot.close()