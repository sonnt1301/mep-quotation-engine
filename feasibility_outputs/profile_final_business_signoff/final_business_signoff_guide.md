# Final Business Sign-off Guide – Phase 2J

Tài liệu hướng dẫn phê duyệt nghiệp vụ cuối cùng trước khi chuyển sang Phase thiết kế write executor ghi thật.

---

## 1. Hướng Dẫn Review Quyết Định Trên Excel

Reviewer thực hiện mở tệp Excel `final_business_signoff_template.xlsx` và điền quyết định tại cột `human_decision` (Cột M) của sheet `Sign-off Items`:
- **APPROVE_FOR_EXECUTOR_DESIGN**: Duyệt vật tư này chuyển tiếp sang Phase thiết kế executor ghi thật.
- **REJECT / NEEDS_CORRECTION / NEEDS_SOURCE_REVIEW**: Từ chối hoặc yêu cầu sửa đổi parser upstream. **Bắt buộc điền Human Note lý do tương ứng (Cột N).**

## 2. Tiêu Chí Để Đạt Trạng Thái APPROVED

Gói Business Sign-off chỉ được xem là phê duyệt hoàn toàn khi:
- [ ] 100% các dòng sign-off được duyệt ở trạng thái `APPROVE_FOR_EXECUTOR_DESIGN`.
- [ ] Mọi ready flags vẫn giữ chặt là `FALSE` bảo mật an toàn.

---

> [!IMPORTANT]
> **BƯỚC TIẾP THEO SAU PHASE 2J**
> * Bước tiếp theo chỉ được bắt đầu khi đã có **target contract thật** của main pipeline/database.
