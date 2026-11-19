"""Outgoing e-mail. With SMTP_HOST set the message goes out through SMTP; without it (development, tests) the
message is written to the log, so the "forgot password" flow can be tried without a mail account."""
import logging
import smtplib
from email.message import EmailMessage

from ... import config

log = logging.getLogger("unicart.mail")


class Mailer:
    def __init__(self, host: str | None = None, port: int | None = None, user: str | None = None,
                 password: str | None = None, sender: str | None = None):
        self.host = config.SMTP_HOST if host is None else host
        self.port = config.SMTP_PORT if port is None else port
        self.user = config.SMTP_USER if user is None else user
        self.password = config.SMTP_PASSWORD if password is None else password
        self.sender = sender or config.SMTP_FROM

    def send(self, to: str, subject: str, body: str) -> None:
        """Never raises: this runs after the HTTP response, a mail failure must only be logged."""
        if not self.host:
            log.warning("SMTP_HOST is not set, e-mail not sent. To: %s | Subject: %s\n%s", to, subject, body)
            return
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(body)
        try:
            if self.port == 465:
                smtp = smtplib.SMTP_SSL(self.host, self.port, timeout=15)
            else:
                smtp = smtplib.SMTP(self.host, self.port, timeout=15)
            with smtp:
                if self.port != 465:
                    smtp.starttls()
                if self.user:
                    smtp.login(self.user, self.password)
                smtp.send_message(msg)
        except Exception:
            log.exception("could not send e-mail to %s", to)


def password_reset_mail(token: str) -> tuple[str, str]:
    link = f"{config.PUBLIC_BASE_URL}/dat-lai-mat-khau#token={token}"
    return ("UniCart - Đặt lại mật khẩu",
            "Xin chào,\n\nChúng tôi nhận được yêu cầu đặt lại mật khẩu cho tài khoản UniCart của bạn.\n"
            f"Mở liên kết sau để đặt mật khẩu mới (có hiệu lực {config.PASSWORD_RESET_MINUTES} phút, dùng một lần):\n\n"
            f"{link}\n\nNếu bạn không yêu cầu, hãy bỏ qua thư này: mật khẩu của bạn không thay đổi.\n\nUniCart")
