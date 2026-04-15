import resend
from ..config import settings

resend.api_key = settings.resend_api_key

def send_otp_email(to_email: str, otp_code: str, app_name: str = None):
    name = app_name or settings.app_name
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <h1 style="color: #2caa9a; font-size: 28px;">{name}</h1>
        </div>
        <div style="background: #f8f9fa; border-radius: 12px; padding: 30px; text-align: center;">
            <h2 style="color: #333; margin-bottom: 10px;">🔐 Your OTP Code</h2>
            <p style="color: #666; margin-bottom: 25px;">
                You requested a One-Time Password (OTP) for your {name} account.
                Here is your verification code:
            </p>
            <div style="background: white; border-radius: 8px; padding: 20px; margin: 20px 0;">
                <span style="font-size: 42px; font-weight: bold; color: #2caa9a; 
                             letter-spacing: 8px;">{otp_code}</span>
            </div>
            <div style="text-align: left; background: white; border-radius: 8px; padding: 15px; margin-top: 20px;">
                <p style="color: #333; font-weight: bold;">Important:</p>
                <ul style="color: #666;">
                    <li>This code will expire in <strong>10 minutes</strong></li>
                    <li>Do not share this code with anyone</li>
                    <li>If you didn't request this code, please ignore this email</li>
                </ul>
            </div>
        </div>
        <p style="text-align: center; color: #999; font-size: 12px; margin-top: 20px;">
            This email was sent by {name}
        </p>
    </body>
    </html>
    """
    
    params = {
        "from": f"{name} <{settings.from_email}>",
        "to": [to_email],
        "subject": f"Your {name} verification code: {otp_code}",
        "html": html_content,
    }
    
    return resend.Emails.send(params)