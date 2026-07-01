# Quy tắc hành vi của trợ lý lập trình Antigravity

- **Quy tắc hiển thị đường dẫn tệp tin bắt buộc**: Bất cứ khi nào nhắc đến tên một tệp tin hoặc thư mục trong bất kỳ câu thoại phản hồi nào (bao gồm cả phản hồi trung gian trước khi gọi tool và phản hồi cuối turn), BẮT BUỘC phải viết kèm đường dẫn tuyệt đối đầy đủ thể hiện vị trí tệp tin đó và làm cho nó click được dưới dạng markdown link sử dụng scheme `file://`.
  - *Ví dụ đúng*: `[models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py)`
  - *Lưu ý*: Tuyệt đối không được viết tên file trống không (như `tệp models.py` hay `tệp task.md`) mà không chèn đường dẫn đầy đủ hiển thị rõ ràng vị trí và link click được.
