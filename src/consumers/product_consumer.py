# import requests

# import json
# import logging as log
# from typing import Dict, Any

# from celery import bootsteps
# from kombu import Consumer, Exchange, Queue

# from config.app_vars import MYE_INVENTORY_AND_MAPPING_SERVICE_URL, PRODUCT_EXCHANGE_NAME, PRODUCT_QUEUE_NAME
 

# exchange = Exchange(PRODUCT_EXCHANGE_NAME)
# tiktok_product_queue = Queue(PRODUCT_QUEUE_NAME, exchange, routing_key="")


# def prepare_product_data(product_data: Dict[Any, Any]):
#     payload: Dict[str, Any] = {
#         "channel_uid": product_data.get("store_uuid", ""),
#         "company_uid": product_data.get("company_uuid", ""),
#         "data": [
#             {
#                 "id": str(product_data["id"]),
#                 "sku": product_data.get("sku", ""),
#                 "name": product_data.get("name", ""),
#                 "fba_status": product_data.get("fba_status", False),
#                 "image": product_data.get("image_url", ""),
#                 "remote_product_name": product_data.get("name", ""),
#                 # "remote_product_description": (
#                 #     product_data["description"]
#                 #     if len(product_data["description"]) < 2000
#                 #     else ""
#                 # ),
#                 "remote_product_description": "Test Description",
#                 "product_metadata": product_data.get("product_metadata", {}),
#             }
#         ],
#     }

#     return payload


# class ProductRequestProcess(bootsteps.ConsumerStep):
#     def get_consumers(self, channel):
#         print("Getting Product Consumer")
#         return [
#             Consumer(
#                 channel,
#                 queues=[tiktok_product_queue],
#                 callbacks=[self.on_message],
#                 accept=["json", "text/plain"],
#             )
#         ]

#     def on_message(self, body, message):
#         try:
#             try:
#                 data = json.loads(body)
#             except Exception as e:
#                 data = body

#             payload = prepare_product_data(product_data=data)

#             success = self.post_to_external_api(payload)
#             if success:
#                 log.info(
#                     "product added in miams successfully"
#                 )  # 👈 This removes the message from the queue
#             else:
#                 # try again to post in miama
#                 self.post_to_external_api(payload)

#             message.ack()  # 👈 This removes the message from the queue

#         except Exception as e:
#             log.error(f"Error processing message: {str(e)}", exc_info=True)
#             message.reject()  # 👈 Discards the message (or use .requeue() if desired)

#     def post_to_external_api(self, payload: dict) -> bool:
#         """
#         Replace this with actual HTTP POST request.
#         Returns:
#             bool: True if successful, False otherwise
#         """
#         try:
#             remote_product_add_url = (
#                 MYE_INVENTORY_AND_MAPPING_SERVICE_URL
#                 + "/api/v1/mapping/product/remote-product/add/"
#             )
#             headers = {
#                 "Content-Type": "application/json",
#                 "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiaWQiOiI5OWU4ZmY3Ni00N2RjLTQ3ZTMtYmFhMC1kMzMxYmU0ZTVjOTYiLCJ1c2VyX2VtYWlsIjoiYXppbUBldmlkZW50YmQuY29tIiwiYXZhdGVyX3VybCI6Imh0dHBzOi8vZXZpZGVudGJkLnNncDEuY2RuLmRpZ2l0YWxvY2VhbnNwYWNlcy5jb20vbXllL0YyMDlBODBDMDMuanBnIiwiZXhwIjoxNzQ3MjE1Mjk5LCJOYW1lIjoiRmFyaGFuIE5haGlkIiwicGhvbmUiOiIrMSAoMjM5KSA5NTgtNTM5MiIsImFkZHJlc3MiOiJVdHRhcmEsIEJhbmdsYWRlc2giLCJ0eXBlIjoicGFyZW50IiwiY29tcGFueV91aWQiOiI5NTAwMmJiMC1kMTgyLTRiMWUtYWE4MC05NDA4MGQ0YmVmYzYiLCJuYW1lIjoiUm91Z2ggJiBUb3VnaCIsImNvdW50cnkiOiJVbml0ZWQgS2luZ2RvbSIsInN0YXR1cyI6dHJ1ZSwicGVybWlzc2lvbnMiOlt7ImlkIjoiMmUxMTVlZjQtNGYzMy00YTk0LTk5YWEtYjdjNzhlYmJmNDFkIiwibmFtZSI6IkNoYW5uZWxzIiwidXJsIjoiL3NldHRpbmdzL2NoYW5uZWxzIiwic2VydmljZSI6Im15ZSJ9LHsiaWQiOiJjMTM1OThhZi01NTM3LTQwNGUtODJmOS0wMDg4OWYxYWU1MWYiLCJuYW1lIjoiTG9jYXRpb25zIiwidXJsIjoiL3NldHRpbmdzL2xvY2F0aW9ucyIsInNlcnZpY2UiOiJteWUifSx7ImlkIjoiN2Y3OWIzYjUtMjM1Yy00ZWQxLTg3NmMtNzg3NjllNDViMDFkIiwibmFtZSI6IkNhcnJpZXJzIiwidXJsIjoiL3NldHRpbmdzL2NhcmVlcnMiLCJzZXJ2aWNlIjoibXllIn0seyJpZCI6ImM3ZDBmYmNjLTQ1NDYtNDJhNi1hMDdhLTY5NzJhYjU3OTFjNiIsIm5hbWUiOiJQcm9kdWN0cyIsInVybCI6Ii9zZXR0aW5ncy9wcm9kdWN0cyIsInNlcnZpY2UiOiJteWUifSx7ImlkIjoiNTdhYzI2ZDAtYTc3Yy00MjZjLWJlNzQtNWQ3YjA4NzkzYmYyIiwibmFtZSI6Ik9wZW4gT3JkZXIgUmVwb3J0IiwidXJsIjoiL3JlcG9ydHMvb3Blbi1vcmRlcnMiLCJzZXJ2aWNlIjoibXllIn0seyJpZCI6ImU2MzM3MTRlLWM5YmMtNGNjYS1hMjJmLTM0ZWYxZTMzM2RmMyIsIm5hbWUiOiJTYWxlcyBSZXBvcnQiLCJ1cmwiOiIvcmVwb3J0cy9zYWxlcy1yZXBvcnQiLCJzZXJ2aWNlIjoibXllIn0seyJpZCI6ImVhN2YwYjVhLTc1ZjMtNGNlMC04MDI3LWRjMzcwOGE5NzViNSIsIm5hbWUiOiJTdG9jayBSZXBvcnQiLCJ1cmwiOiIvcmVwb3J0cy9zdG9jay1yZXBvcnQiLCJzZXJ2aWNlIjoibXllIn0seyJpZCI6IjZhYmVjMGMyLWE0MGItNDMyMC04ZTE3LWI1OTY4YmI0NTllZCIsIm5hbWUiOiJpbnZlbnRvcnkiLCJ1cmwiOiIvaW52ZW50b3J5Iiwic2VydmljZSI6Im15ZSJ9LHsiaWQiOiJkYTYxOTI2NS01ODc5LTQ4YTMtYTM0NS04NGU5NDU3ZmNmMTciLCJuYW1lIjoiaW52ZW50b3J5LXZpZXctb25seSIsInVybCI6Ii9pbnZlbnRvcnkiLCJzZXJ2aWNlIjoibXllIn0seyJpZCI6IjliZjE5YzkzLTg0YTItNDIyMC05ZTAxLTFkOWQ3ODU5ZGM1YiIsIm5hbWUiOiJkYXNoYm9hcmQiLCJ1cmwiOiIvZGFzaGJvYXJkIiwic2VydmljZSI6Im15ZSJ9XSwicmVzdHJpY3Rpb25zIjp7InN1YnNjcmliZWQiOmZhbHNlfX0.QQU1Om9-13I-tv83caNzBZucczZOnG7srIgjjKV73xxbbrRPmhf1t-8dU6gnQ-mnojidrxrWt9LmkcOSslz9III-up7y6-OvKKhchBEhgiprsI1GOknO_8jjG_UOLqkjkUCtSreRPrij9w0rOvkUjdGbR5ozAgajEow_yoO1OBJBREjSTYGorimWBybyvlC5M4IiDrwvEMAI4OMSL8MVPl8d7disvGB-x2-yfz6ehCQ0wbosp-qJ-uOnWOlNMMm7TT6rIEI_x0MWeItztlb9-MssECqaKZ_ACA-NBeOnPadHeEgA12sFgB2l2AXcYsHEDMohp0AxYj_5usy2hzFXzw",
#             }

#             print("payload: ", payload)
#             response = requests.post(
#                 remote_product_add_url, json=payload, headers=headers
#             )

#             if int(response.status_code) == 201:
#                 log.info(f"Product sent to MIAMS successfully: {response.json()}")
#                 return True
#             else:
#                 log.warning(
#                     f"Failed to send product to MIAMS: {response.status_code} - {response.text}"
#                 )
#                 return False

#         except Exception as e:
#             log.error(f"Failed to send to MIAMS: {str(e)}", exc_info=True)
#             return False


# # cel_app.steps["consumer"].add(ProductRequestProcess)
