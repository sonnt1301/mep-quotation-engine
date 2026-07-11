# Controlled Commit Plan – Phase 2C

Tài liệu này định nghĩa kế hoạch ghi nhận có kiểm soát (Controlled Commit Plan) và phân tích rủi ro an toàn cho Write Candidates trước khi tiến hành Phase 2D (ghi thật vào main pipeline).

---

> [!WARNING]
> **CẢNH BÁO AN TOÀN CHƯA GHI THẬT**
> * Kế hoạch này **CHƯA** thực hiện ghi bất kỳ dữ liệu nào vào database hoặc main production pipeline của dự án.
> * Trạng thái an toàn: `ready_for_write_to_main_pipeline = FALSE`.

---

## 1. Trạng Thái Của Đệ Trình (Proposed Status)

* Proposed status: `READY_FOR_HUMAN_COMMIT_REVIEW`
* Ready for write to main pipeline: `FALSE`
* Lý do chưa sẵn sàng ghi thật:
  - Chưa có chữ ký số hoặc Human Approval duyệt file Excel Controlled Commit.

## 2. Thống Kê Số Lượng Candidates

* Số lượng ghi dự kiến (candidate_items_count): `3`
* Số lượng bị loại bỏ (skipped_items_count): `0`
* Số lượng trùng khóa ghi (duplicate_write_key_count): `0`
* Số lượng trùng mã hàng cảnh báo (duplicate_material_code_count): `0`

## 3. Điều Kiện Để Tiến Hành Ghi Thật (Phase 2D Commit Criteria)

Để được phép chuyển đổi biến `ready_for_write_to_main_pipeline` sang `TRUE` và tiến hành ghi dữ liệu thật, hệ thống bắt buộc phải thỏa mãn các tiêu chí sau:

- [ ] **Tiêu chí 1: Có Candidate hợp lệ**
  - Số lượng `candidate_items_count` phải lớn hơn 0.
- [ ] **Tiêu chí 2: Triệt tiêu hoàn toàn trùng lặp khóa**
  - Số lượng `duplicate_write_key_count` phải bằng 0 (hoặc tất cả các dòng trùng lặp phải được con người duyệt qua và phân xử thủ công trong file Excel).
- [ ] **Tiêu chí 3: Không còn dòng ở trạng thái rủi ro**
  - Không có dòng nào của đệ trình đang ở trạng thái `NEEDS_INVESTIGATION` hoặc `REJECT` chưa được phân xử.
- [ ] **Tiêu chí 4: Human Approval trên file Excel**
  - Người dùng / Reviewer đã mở file [write_candidate_review.xlsx](file:///D:/mep_quotation_pipeline/feasibility_outputs/profile_write_candidate/write_candidate_review.xlsx) kiểm tra trực quan các sheet và ký duyệt chấp thuận kế hoạch.
- [ ] **Tiêu chí 5: Có phương án Backup và Phục hồi (Rollback Plan)**
  - Đã thực hiện sao lưu trạng thái database hiện tại của main pipeline trước khi chạy lệnh ghi.

---

## 4. Các Tệp Tin Preview Cục Bộ
* Tệp Candidates JSON: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_candidate\write_candidate_items.json`
* Tệp Summary JSON: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_candidate\write_candidate_summary.json`
* Bảng Excel Review: `D:\mep_quotation_pipeline\feasibility_outputs\profile_write_candidate\write_candidate_review.xlsx`
