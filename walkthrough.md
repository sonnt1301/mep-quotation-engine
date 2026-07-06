# Tài Liệu Nghiệm Thu Walkthrough – Phase 14 (Source Profiling Gate)

Tài liệu này tóm tắt kết quả triển khai và kết quả kiểm định chất lượng của Phase 14, bao gồm cả các cải tiến sửa lỗi mới nhất.

---

## Các Thay Đổi Đã Thực Hiện

### 1. Mô hình Pydantic & JSON Schema (spec)
* **Tệp chỉnh sửa**: [models.py (D:/mep_quotation_pipeline/mep_quotation/spec/models.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/models.py) và [__init__.py (D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)](file:///D:/mep_quotation_pipeline/mep_quotation/spec/__init__.py)
* **Kết quả**: Thêm các enums `SourceRole`, `RecommendedNextAction` và các mô hình `SourceProfileModel`, `TechnicalReadabilityModel`, `SourceDateCandidateModel`. Cập nhật `FilePathsModel` với trường `source_profile`.
* **Đồng bộ hóa**: Chạy kịch bản `generate_schemas.py` và sinh thành công JSON Schema cho `source_profile.schema.json`.

### 2. Sửa Phạm Vi Định Dạng WEBP (webp scope)
* **Tệp chỉnh sửa**: [profiler.py (D:/mep_quotation_pipeline/mep_quotation/intake/profiler.py)](file:///D:/mep_quotation_pipeline/mep_quotation/intake/profiler.py)
* **Kết quả**: 
  * Tách định dạng `.webp` khỏi nhóm `image` deep profiling để không đọc Pillow / không deep read.
  * Chuyển `.webp` vào nhóm limited support cùng `.xls`, `.xlsm`, `.csv`. 
  * Đặt `is_supported_file_type = False`, gán warning `limited_support` và `recommended_next_action = RecommendedNextAction.unsupported_file_type`.

### 3. Sửa Atomic Write thành Atomic Replace thực sự
* **Tệp chỉnh sửa**: [main.py (D:/mep_quotation_pipeline/mep_quotation/cli/main.py)](file:///D:/mep_quotation_pipeline/mep_quotation/cli/main.py)
* **Kết quả**: Sử dụng lệnh đổi tên nguyên tử `os.replace` để thay thế file thay vì sử dụng `os.remove` trước. Áp dụng cho cả tệp `source_profile.json` và cập nhật `package.json`.

### 4. Tích Hợp Kiểm Định & Tương Thích Ngược
* **Tệp chỉnh sửa**: [integrity.py (D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)](file:///D:/mep_quotation_pipeline/mep_quotation/package/integrity.py)
* **Kết quả**:
  * Kiểm định chéo: xác thực cấu trúc `SourceProfileModel`, đối chiếu `quotation_id`, kiểm định SHA256 file nguồn.
  * Tương thích ngược: pass bình thường nếu package cũ (Phase 1-13) chưa chạy profiling và chưa khai báo. Báo lỗi nghiêm trọng nếu có khai báo trong metadata nhưng file thực tế bị mất mát trên đĩa.

### 5. Tích Hợp UI
* **Tệp chỉnh sửa**: [local_review_app.py (D:/mep_quotation_pipeline/tools/local_review_app.py)](file:///D:/mep_quotation_pipeline/tools/local_review_app.py)
* **Kết quả**: Thêm tab **Hồ sơ nguồn (Source Profile)** hiển thị chi tiết và trực quan các kết quả phân tích trong mục Artifacts Viewer nâng cao.

---

## Kết Quả Kiểm Thử (Verification Results)

### 1. Bộ kiểm thử tự động
* **Tệp chỉnh sửa**: [test_profile_source.py (D:/mep_quotation_pipeline/tests/test_profile_source.py)](file:///D:/mep_quotation_pipeline/tests/test_profile_source.py)
* **Mô tả bổ sung**:
  * **Test tệp WEBP**: Thêm test case cho `original.webp` xác nhận hệ thống không thực hiện deep profiling, gán `is_supported = False` và ghi nhận warning `limited_support` cũng như `recommended_next_action` không phải `run_image_ocr_pipeline_later`.
  * **Test CLI overwrite**: Kiểm thử verify tệp `.json` sinh ra là tệp JSON hợp lệ và không để lại file `.tmp` thừa sau khi thực hiện atomic overwrite.

### 2. Kết quả chạy pytest
Tất cả các bài kiểm thử đã vượt qua thành công:
```bash
============================ 148 passed in 11.29s =============================
```
Mã nguồn hoạt động ổn định và đạt tiêu chuẩn nghiệm thu tuyệt đối.
