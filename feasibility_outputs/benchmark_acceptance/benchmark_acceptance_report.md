# Báo Cáo Nghiệm Thu Acceptance Benchmark – Milestone E

Báo cáo này tổng kết kết quả đánh giá nghiệm thu khả thi bóc tách (Acceptance Benchmark) cho hai nhà cung cấp **ABB** và **LS** dựa trên các tiêu chí cố định (Acceptance Criteria).

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Tổng Hợp

| Nhà Cung Cấp | Trạng Thái Đánh Giá | Số Vật Tư Hợp Lệ (Valid) | Số Vật Tư Bị Loại (Invalid) | Số Trang Đạt PASS | Tổng Số Trang |
| --- | --- | --- | --- | --- | --- |
| **ABB** | `PASS` | 743 | 2 | 13 | 13 |
| **LS** | `ACCEPTED_WITH_KNOWN_LIMITATIONS` | 284 | 16 | 3 | 5 |

---

## 2. Bảng Kiểm Tra Chi Tiết (Checks Table)

### Hãng ABB (Target: `PASS`)
| Tên Hạng Mục Kiểm Tra | Trạng Thái | Chi Tiết |
| --- | --- | --- |
| `abb_exact_count_match` | **PASS** | Valid: 743/743, Invalid: 2/2 |
| `abb_pass_pages_match` | **PASS** | PASS pages: 13/13 |
| `output_contract_compliance` | **PASS** | All items comply with JSON output contract. |
| `abb_exact_baseline_alignment` | **PASS** | 100% match with baseline v1 items. |

### Hãng LS (Target: `ACCEPTED_WITH_KNOWN_LIMITATIONS`)
| Tên Hạng Mục Kiểm Tra | Trạng Thái | Chi Tiết |
| --- | --- | --- |
| `ls_minimum_count_match` | **PASS** | Valid: 284 (criteria >=282), Invalid: 16 (criteria <=19) |
| `ls_minimum_pass_pages` | **PASS** | PASS pages: 3 (criteria >=3) |
| `output_contract_compliance` | **PASS** | All items comply with JSON output contract. |
| `ls_no_10x_price_mismatch` | **PASS** | No LS items deviate >10x from baseline v1. |
| `ls_price_regression_protection` | **PASS** | All LS price regressions passed. |
| `ls_large_price_protection` | **PASS** | All large LS prices protected. |

---

## 3. Các Giới Hạn Đã Biết (Known Limitations)

### Hãng ABB
* Không có giới hạn nghiêm trọng. Cấu hình layout đạt trạng thái Feasibility rất tốt.

### Hãng LS
* **Trang 2 và Trang 5 vẫn ở trạng thái PARTIAL** (chưa đạt tỷ lệ lỗi <= 5% hoặc chưa đủ số lượng item tối thiểu trên mỗi trang để PASS tuyệt đối). Việc tối ưu hóa các trang này sẽ cần các bước hardening profile sâu hơn trong tương lai.

---

## 4. Đề Xuất & Khuyến Nghị Cuối Cùng (Final Recommendation)

1. **Khả năng Benchmark**: Kết quả bóc tách của cả ABB và LS bằng tệp cấu hình JSON động đã đạt tính ổn định rất cao và có thể dùng làm benchmark nền tảng để so sánh cho các Supplier Profile Parser tiếp theo.
2. **Trạng thái Tích hợp**: **Chưa tích hợp vào pipeline chính.** Dữ liệu đầu ra tuân thủ nghiêm ngặt chuẩn hợp đồng [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json) nhưng mới chỉ nằm ở lớp Feasibility.
3. **Các Bước Tiếp Theo**: Sau Milestone E, dự án có thể lựa chọn:
   * **Phương án 1**: Tiếp tục Hardening profile cho hãng LS để nâng cao tỷ lệ PASS của các trang PARTIAL.
   * **Phương án 2**: Mở rộng Parser sang nhà cung cấp thứ 3 bằng cách viết tệp cấu hình JSON tương tự.
   * **Phương án 3**: Thiết kế cầu nối tích hợp (Integration Bridge) để đẩy kết quả từ Config Runner sang pipeline chính của dự án.