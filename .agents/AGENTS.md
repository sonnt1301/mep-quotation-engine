# Custom Rules for MEP Quotation Pipeline Project

- **Báo cáo và tài liệu**: Khi kết thúc công việc hoặc báo cáo tiến độ/nghiệm thu, luôn đính kèm đường link click được (sử dụng định dạng link file markdown `[basename](file:///path/to/file)`) của các tệp báo cáo quan trọng như `walkthrough.md`, `task.md` hoặc `implementation_plan.md` ở thư mục dự án để người dùng dễ dàng chuyển giao cho các AI khác kiểm tra.

- **BẮT BUỘC – Link tài liệu sau mỗi kế hoạch**: Mỗi khi tạo hoặc cập nhật `implementation_plan.md`, `task.md`, `walkthrough.md` (dù là Artifact hay file trong dự án), phải:
  1. **Copy file** từ brain artifact về thư mục gốc của dự án hiện hành (dùng `-Force` để ghi đè).
  2. **IN đường link ngắn gọn** dạng link clickable + đường dẫn thô ngay trong phản hồi đó dựa trên thư mục dự án thực tế.

  **Format bắt buộc (với <project_root> là đường dẫn tuyệt đối của thư mục dự án hiện hành)**:
  - [implementation_plan.md](file:///<project_root>/implementation_plan.md) (`<project_root>\implementation_plan.md`)
  - [task.md](file:///<project_root>/task.md) (`<project_root>\task.md`)
  - [walkthrough.md](file:///<project_root>/walkthrough.md) (`<project_root>\walkthrough.md`)



