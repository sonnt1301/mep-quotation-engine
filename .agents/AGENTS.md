# Custom Rules for MEP Quotation Pipeline Project

- **Báo cáo và tài liệu**: Khi kết thúc công việc hoặc báo cáo tiến độ/nghiệm thu, luôn đính kèm đường link click được (sử dụng định dạng link file markdown `[basename](file:///path/to/file)`) của các tệp báo cáo quan trọng như `walkthrough.md`, `task.md` hoặc `implementation_plan.md` ở thư mục dự án để người dùng dễ dàng chuyển giao cho các AI khác kiểm tra.

- **BẮT BUỘC – Link tài liệu sau mỗi kế hoạch**: Mỗi khi tạo hoặc cập nhật `implementation_plan.md`, `task.md`, `walkthrough.md` (dù là Artifact hay file trong dự án), phải:
  1. **Copy file** từ brain artifact về thư mục dự án `D:\mep_quotation_pipeline\` (dùng `-Force` để ghi đè).
  2. **IN đường link ngắn gọn** dạng link clickable + đường dẫn thô ngay trong phản hồi đó.

  **Format bắt buộc**:
  - [implementation_plan.md](file:///D:/mep_quotation_pipeline/implementation_plan.md) (`D:\mep_quotation_pipeline\implementation_plan.md`)
  - [task.md](file:///D:/mep_quotation_pipeline/task.md) (`D:\mep_quotation_pipeline\task.md`)
  - [walkthrough.md](file:///D:/mep_quotation_pipeline/walkthrough.md) (`D:\mep_quotation_pipeline\walkthrough.md`)


