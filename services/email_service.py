"""
Servicio de email masivo asíncrono usando aiosmtplib (Gmail SMTP).
Se ejecuta como BackgroundTask de FastAPI para no bloquear el servidor.
"""
import asyncio
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime

import aiosmtplib
from sqlalchemy.orm import Session

from database import SessionLocal
from models.crm import EmailCampaign, EmailSend
import config


async def send_campaign(campaign_id: int) -> None:
    """
    Worker principal. Abre una sola conexión SMTP para todo el batch.
    Actualiza el status de cada envío en tiempo real.
    """
    db: Session = SessionLocal()
    try:
        campaign = db.get(EmailCampaign, campaign_id)
        if not campaign:
            return

        campaign.status = "enviando"
        db.commit()

        sends = (
            db.query(EmailSend)
            .filter(EmailSend.campaign_id == campaign_id, EmailSend.status == "pendiente")
            .all()
        )

        sent = 0
        failed = 0

        try:
            smtp = aiosmtplib.SMTP(
                hostname=config.SMTP_HOST,
                port=config.SMTP_PORT,
                use_tls=False,
            )
            await smtp.connect()
            await smtp.starttls()
            await smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)

            for send in sends:
                try:
                    msg = MIMEMultipart("alternative")
                    msg["Subject"] = campaign.asunto
                    msg["From"] = f"{config.SMTP_FROM_NAME} <{config.SMTP_USER}>"
                    msg["To"] = send.email
                    msg.attach(MIMEText(campaign.html_body, "html", "utf-8"))

                    await smtp.send_message(msg)
                    send.status = "enviado"
                    send.sent_at = datetime.utcnow()
                    sent += 1
                except Exception as e:
                    send.status = "fallido"
                    send.error_msg = str(e)[:300]
                    failed += 1

                db.commit()
                await asyncio.sleep(0.1)  # ~10 emails/seg

            await smtp.quit()

        except Exception as conn_err:
            # La conexión SMTP falló — marcar todo como fallido
            for send in sends:
                if send.status == "pendiente":
                    send.status = "fallido"
                    send.error_msg = f"SMTP connection error: {str(conn_err)[:200]}"
                    failed += 1
            db.commit()

        campaign.status = "completado" if failed == 0 else ("completado" if sent > 0 else "error")
        campaign.total_enviados = sent
        campaign.total_fallidos = failed
        campaign.enviado_en = datetime.utcnow().isoformat()
        db.commit()

    finally:
        db.close()
