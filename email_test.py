import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

try:
    msg = MIMEMultipart()
    msg['From'] = 'biodiversitynexus@yahoo.com'
    msg['To'] = 'bikorimanadesire5@gmail.com'
    msg['Subject'] = 'SMTP Test'
    body = 'This is a test email.'
    msg.attach(MIMEText(body, 'plain'))

    server = smtplib.SMTP('smtp.mail.yahoo.com', 587)
    server.starttls()
    server.login('biodiversitynexus@yahoo.com', 'wwiyxralunhassow')
    text = msg.as_string()
    server.sendmail('biodiversitynexus@yahoo.com', 'bikorimanadesire5@gmail.com', text)
    server.quit()
    print("Email sent successfully")
except Exception as e:
    print(f"Failed to send email: {e}")
