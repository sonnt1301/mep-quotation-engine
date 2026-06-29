\# MEP Quotation Engine



\# Sprint 0 - Foundation



\*\*Status:\*\* Hoàn thành

\*\*Release:\*\* v0.1.0

\*\*Ngày hoàn thành:\*\* 2026-06-29



\---



\# Mục tiêu Sprint



Xây dựng nền móng của toàn bộ hệ thống.



Sprint này \*\*không tập trung vào AI\*\*, \*\*không tập trung vào PDF Parser\*\*, \*\*không tập trung vào OCR\*\*.



Mục tiêu duy nhất là xây dựng \*\*Data Contract\*\* và \*\*Foundation Architecture\*\* ổn định để toàn bộ các Sprint sau sử dụng chung.



\---



\# Đã hoàn thành



\## 1. Quotation Package Specification v1.0



Thiết kế chuẩn Quotation Package.



Mỗi báo giá là một Package độc lập.



Cấu trúc Package gồm:



\* package.json

\* source/original.pdf

\* parsed/

\* normalized/

\* corrections/

\* logs/



\---



\## 2. Pydantic Models



Pydantic v2 được sử dụng làm \*\*Source of Truth\*\*.



Toàn bộ JSON Schema được generate từ Pydantic Models.



Không tồn tại hai nguồn định nghĩa dữ liệu.



\---



\## 3. Package Builder



Đã triển khai:



\* Create Package

\* Load Package

\* Validate Package

\* Write Package



\---



\## 4. Validation



Kiểm tra:



\* quotation\_id

\* supplier\_code

\* quotation\_date

\* package integrity

\* schema version



Phát hiện và từ chối dữ liệu không hợp lệ ngay từ đầu.



\---



\## 5. Corrections



Thiết kế corrections.json.



Hỗ trợ lưu:



\* user

\* timestamp

\* field\_path

\* old\_value

\* new\_value

\* reason



Đây sẽ là dữ liệu phục vụ AI learning trong các phiên bản sau.



\---



\## 6. Audit Logger



Thiết kế Event Logger.



Log theo định dạng JSONL.



Có thể append.



Không overwrite dữ liệu cũ.



\---



\## 7. Material Index



Đọc toàn bộ normalized.json.



Sinh material\_index.json.



Hỗ trợ tìm kiếm theo:



\* Material Code

\* Material Name



Có Strict Mode và Non-Strict Mode.



\---



\## 8. CLI



Đã có các lệnh:



\* create-package

\* validate-package

\* record-correction

\* build-index

\* search-material



\---



\## 9. Testing



Hoàn thành toàn bộ Unit Tests.



Kết quả:



\* \*\*21/21 tests passed\*\*



\---



\## 10. Git \& GitHub



Đã thiết lập:



\* Git Repository

\* GitHub Repository

\* main branch

\* feature branch workflow

\* Git Tag

\* GitHub Release

\* Conventional Commits



Release hiện tại:



\*\*v0.1.0\*\*



\---



\# Kiến trúc hiện tại



```text

Foundation

&#x20;       │

&#x20;       ▼

Quotation Package

&#x20;       │

&#x20;       ▼

Validation

&#x20;       │

&#x20;       ▼

Corrections

&#x20;       │

&#x20;       ▼

Audit

&#x20;       │

&#x20;       ▼

Material Index

```



Đây là nền móng của toàn bộ hệ thống.



\---



\# Chưa triển khai



Các hạng mục sau \*\*chưa nằm trong Sprint 0\*\*:



\* PDF Validation

\* PDF Metadata

\* PDF Import

\* PDF Parser

\* OCR

\* Docling

\* AI / LLM Integration

\* parsed/quotation.json generation

\* parsed/quotation.md generation

\* normalized.json generation từ PDF/parser

\* BOQ Matching

\* Evidence Viewer

\* Supplier Comparison

\* Database

\* Web Application

\* API



\---



\# Quy tắc phát triển



\* Mỗi Sprint chỉ có \*\*một mục tiêu duy nhất\*\*.

\* Không mở rộng scope giữa Sprint.

\* Không thêm AI khi hạ tầng chưa hoàn thiện.

\* Foundation chỉ được chỉnh sửa khi phát hiện bug hoặc lỗi thiết kế nghiêm trọng.



\---



\# Chuẩn bị cho Sprint 1 (Release v0.2.0)



Sprint tiếp theo sẽ triển khai:



\*\*PDF Intake Layer\*\*



Mục tiêu:



\* Import PDF

\* Validate PDF

\* Sinh metadata.json

\* Cập nhật package.json

\* Lưu original.pdf vào Quotation Package



Sprint này \*\*không parse PDF\*\*, \*\*không OCR\*\*, \*\*không AI\*\*.



Hoàn thành Sprint này sẽ tạo nền tảng để bắt đầu PDF Parsing ở Release \*\*v0.3.0\*\*.



