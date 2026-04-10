import boto3
import os
from dotenv import load_dotenv

load_dotenv()

def _get_sns_client():
    """Creates and returns a boto3 SNS client using env credentials."""
    session_token = os.getenv("AWS_SESSION_TOKEN")

    kwargs = {
        "region_name": os.getenv("AWS_REGION", "us-east-1"),
        "aws_access_key_id": os.getenv("AWS_ACCESS_KEY_ID"),
        "aws_secret_access_key": os.getenv("AWS_SECRET_ACCESS_KEY"),
    }
    # Learner Lab requires a session token
    if session_token:
        kwargs["aws_session_token"] = session_token

    return boto3.client("sns", **kwargs)


def send_sms(phone_number: str, message: str) -> dict:
    """
    Send a direct SMS to a phone number via AWS SNS.
    phone_number must be in E.164 format, e.g. '+14155552671'
    Returns the SNS MessageId on success.
    """
    if not phone_number or not message:
        return {"error": "phone_number and message are required"}

    try:
        client = _get_sns_client()
        response = client.publish(
            PhoneNumber=phone_number,
            Message=message,
            MessageAttributes={
                "AWS.SNS.SMS.SMSType": {
                    "DataType": "String",
                    "StringValue": "Transactional",  # High priority delivery
                }
            },
        )
        print(f"[SNS] SMS sent to {phone_number}. MessageId: {response['MessageId']}")
        return {"message_id": response["MessageId"]}
    except Exception as e:
        print(f"[SNS] Failed to send SMS to {phone_number}: {e}")
        return {"error": str(e)}


def publish_to_topic(message: str, subject: str = "PulseOps Alert") -> dict:
    """
    Publish a message to the configured SNS topic ARN.
    Useful for broadcasting to multiple subscribers (email/SMS).
    """
    topic_arn = os.getenv("SNS_TOPIC_ARN")
    if not topic_arn:
        print("[SNS] SNS_TOPIC_ARN not configured, skipping topic publish.")
        return {"error": "SNS_TOPIC_ARN not set"}

    try:
        client = _get_sns_client()
        response = client.publish(
            TopicArn=topic_arn,
            Message=message,
            Subject=subject,
        )
        print(f"[SNS] Published to topic {topic_arn}. MessageId: {response['MessageId']}")
        return {"message_id": response["MessageId"]}
    except Exception as e:
        print(f"[SNS] Failed to publish to topic: {e}")
        return {"error": str(e)}


# ── Convenience helpers used directly in app.py ─────────────────────────────

def notify_high_priority_surgery(hospital_name: str, patient_name: str,
                                  surgery_type: str, preferred_date: str,
                                  contact_phone: str | None = None) -> None:
    """
    Fires an SMS + topic notification when a HIGH priority surgery is booked.
    contact_phone: optional direct number to also text (E.164 format).
    """
    msg = (
        f"[PulseOps ALERT] HIGH Priority Surgery Requested\n"
        f"Hospital : {hospital_name}\n"
        f"Patient  : {patient_name}\n"
        f"Type     : {surgery_type}\n"
        f"Date     : {preferred_date}\n"
        f"Immediate scheduling required."
    )
    publish_to_topic(msg, subject="HIGH Priority Surgery Alert")
    if contact_phone:
        send_sms(contact_phone, msg)


def notify_low_inventory(hospital_name: str, item_name: str,
                          current_stock: int, min_stock: int,
                          contact_phone: str | None = None) -> None:
    """
    Fires an SMS + topic notification when an inventory item is below min_stock.
    contact_phone: optional direct number to also text (E.164 format).
    """
    msg = (
        f"[PulseOps ALERT] Low Inventory\n"
        f"Hospital : {hospital_name}\n"
        f"Item     : {item_name}\n"
        f"Stock    : {current_stock} (min: {min_stock})\n"
        f"Please reorder immediately."
    )
    publish_to_topic(msg, subject="Low Inventory Alert")
    if contact_phone:
        send_sms(contact_phone, msg)
