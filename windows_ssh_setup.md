# 🪟 How to Setup SSH on Windows (Passwordless)

Follow these steps on your **WINDOWS Machine** to enable remote control.

### 1. Install OpenSSH Server
1. Open **Settings** > **Apps** > **Optional features**.
2. Click **View features** (or "Add a feature").
3. Search for **OpenSSH Server** and install it.
4. Restart your computer if prompted.

### 2. Start the SSH Service
1. Open **PowerShell** as Administrator.
2. Run these commands to start the service and make it run on startup:
   ```powershell
   Start-Service sshd
   Set-Service -Name sshd -StartupType 'Automatic'
   ```
3. Check if it's running:
   ```powershell
   Get-Service sshd
   ```

### 3. Add Your Linux Key (For Passwordless Access)
1. On Windows, create the `.ssh` directory for your user (Achu Pradeep):
   *   Open PowerShell and run:
       ```powershell
       mkdir "C:\Users\achup\.ssh"
       ```
2. Create the `authorized_keys` file:
   *   Open Notepad.
   *   Paste the **Public Key** below into it.
   *   Save the file as `C:\Users\achup\.ssh\authorized_keys`. (Select "All Files" in Notepad so it doesn't add .txt).
   *   **IMPORTANT**: The file must have NO extension.

**🔑 YOUR PUBLIC KEY (Paste this):**
```text
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAACAQDiGLed7bslqPgsocn7m2XhNh5WiWYE+9qWhBTxg4Z83dy9UStbdmHKbkPb+uCbqNq3H/9Gqpu4vn5fX+1cDnx5nfJQjQofcV+zsb+pjvvOR5oHrIjDV3wn7oJplZYdUaqbZknJGgIZeWGZ5rAw4UXSOC0sBLz2uPf0nWPp0ivyQFcBY30qji+WXeNEbbKK1BtrMFe5uyDyqGDs/Nf8915J3j0DrkeQnkK/iPRY3SCdUJg4XDeF7bq3JHJyIkTTDaTSXPginz0cxA8AkEqfNCiHfdfgW1ymy+GJa5zTbgMgk5ikUhcDd93r3j6znwIE1LQsLo0Rf4WOmRrbVHRCtI8btrHAXcH1IgpoOHQ4eolWgpOXrcyF3/SfO4g6u71UTRGf7vD7a47BZytkUEd2AMOr1ZmadPh9W/IG1TAVpp4NXF9eZClCvcfwExGtoAMLTYoyGlhHE4j+dAWCIaEKxegc+xT8F7Q2FIt2x6wbr5L+k2wlndb7aKzXXdikRU0CMCBoGeRdd2AuD7rkSRySO+XhwC4Pmazd92v1I/AmHrRAvErcJP/A1boAOOwZ4OBgmOBps55Njzs4sknQW4jcvCDRNm6FEk+pC9Vd56EGKQgx1UzpxGI96Zyk7KCA5+M9LqOj/IIeF5g/isUEbciWAGyxOdO3AxCfKloHauOJhA69IQ== achu@achu-Legion
```

### 4. Permissions (Important!)
Windows SSH can be strict about permissions.
1. Locate `C:\Users\achup\.ssh\authorized_keys`.
2. Right-click > **Properties** > **Security** > **Advanced**.
3. **Disable Inheritance**.
4. Remove all entries EXCEPT **System**, **Administrators**, and **Achu Pradeep**.
5. Ensure your user has "Full Control".

### 5. Test It
From your Linux terminal, run:
```bash
ssh "Achu Pradeep@192.168.122.121"
```
It should let you in without a password!
