# Báo Cáo Nghiệm Thu Acceptance Benchmark – Milestone F

Báo cáo này tổng kết kết quả đánh giá nghiệm thu khả thi bóc tách (Acceptance Benchmark) cho cả ba nhà cung cấp **ABB**, **LS** và **CHINT** dựa trên các tiêu chí cố định (Acceptance Criteria).

---

> [!WARNING]
> **PHẠM VI TRIỂN KHAI**
> * Toàn bộ các công việc trong giai đoạn này chỉ phục vụ mục tiêu **Khảo sát Khả thi (Feasibility Reset)**.
> * **Không tích hợp vào pipeline chính của dự án và không sửa đổi giao diện Streamlit UI.**
> * **Không OCR, không AI/LLM, không parse Excel.**
> * **Không hardcode dữ liệu đầu ra chỉ để pass test.**
> * Chưa sẵn sàng cho môi trường vận hành thực tế (Not Production-Ready).

---

## 1. Kết Quả Nghiệm Thu Tổng Hợp

| Nhà Cung Cấp | Trạng Thế Đánh Giá | Số Vật Tư Hợp Lệ (Valid) | Số Vật Tư Bị Loại (Invalid) | Số Trang Đạt PASS | Tổng Số Trang |
| --- | --- | --- | --- | --- | --- |
| **ABB** | `PASS` | 743 | 2 | 13 | 13 |
| **LS** | `ACCEPTED_WITH_KNOWN_LIMITATIONS` | 284 | 16 | 3 | 5 |
| **CHINT** | `ACCEPTED_WITH_KNOWN_LIMITATIONS` | 45 | 6 | 1 | 3 |

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

### Hãng CHINT (Target: `ACCEPTED_WITH_KNOWN_LIMITATIONS`)
| Tên Hạng Mục Kiểm Tra | Trạng Thái | Chi Tiết |
| --- | --- | --- |
| `chint_valid_items_count` | **PASS** | Valid items: 45 (criteria >=20) |
| `chint_invalid_items_count` | **PASS** | Invalid items: 6 (criteria <=15) |
| `chint_total_pages_count` | **PASS** | Total pages: 3 (criteria ==3) |
| `chint_pass_pages_count` | **PASS** | PASS pages: 1 (criteria >=1) |
| `chint_partial_pages_count` | **PASS** | PARTIAL pages: 2 (criteria <=2) |
| `output_contract_compliance` | **PASS** | All items comply with JSON output contract. |

---

## 3. Các Giới Hạn Đã Biết (Known Limitations)

### Hãng ABB
* Không có giới hạn nghiêm trọng. Cấu hình layout đạt trạng thái Feasibility rất tốt.

### Hãng LS
* **Trang 2 và Trang 5 vẫn ở trạng thái PARTIAL** (chưa đạt tỷ lệ lỗi <= 5% hoặc chưa đủ số lượng item tối thiểu trên mỗi trang để PASS tuyệt đối). Việc tối ưu hóa các trang này sẽ cần các bước hardening profile sâu hơn trong tương lai.

### Hãng CHINT
* **Trang 3 và Trang 5 vẫn ở trạng thái PARTIAL** do có một số dòng tiêu đề hoặc dòng text thông số phụ bị validator loại thành invalid. Có thể tiếp tục tinh chỉnh lề min_y/max_y hoặc logic validator để nâng cao độ phủ.

---

## 4. Đề Xuất & Khuyến Nghị Cuối Cùng (Final Recommendation)

1. **Khả năng Benchmark**: Việc onboard CHINT cho thấy tín hiệu khả thi ban đầu khi áp dụng quy trình Supplier Profile Config cho nhà cung cấp thứ 3. Tuy nhiên, do CHINT mới đạt 1/3 trang PASS và còn 2/3 trang PARTIAL, kết quả này chưa đủ để kết luận framework có tính tổng quát cao. Cần tiếp tục hardening thêm supplier và layout trước khi tích hợp pipeline chính.
2. **Trạng thái Tích hợp**: **Chưa tích hợp vào pipeline chính.** Dữ liệu đầu ra tuân thủ nghiêm ngặt chuẩn hợp đồng [profile_output_contract.json](file:///D:/mep_quotation_pipeline/tools/feasibility/profile_output_contract.json).
3. **Các Bước Tiếp Theo**: Sau Milestone F, dự án có thể:
   * Tiếp tục Hardening profile cho hãng LS và CHINT để tăng số trang đạt PASS.
   * Thiết kế cầu nối tích hợp (Integration Bridge) để đẩy kết quả từ Config Runner sang pipeline chính của dự án.