# RULES

## Mission
- Project nay chi duoc phep nghien cuu va doc chi so app bang du lieu app/UI hierarchy.
- Scope hien tai la man `PET SANCTUARY`.

## Hard Rules
- Tuyet doi khong su dung OCR duoi moi hinh thuc.
- Tuyet doi khong de xuat OCR lam fallback.
- Khong import, tham chieu, hoac phu thuoc vao `pytesseract`, OCR API, hay bat ky text reader kieu OCR nao.
- Khong "tam dung OCR cho nhanh" trong local debug, script test, hay code production.
- Tuyet doi khong doc screenshot, template match screenshot, hay suy luan token tu pixel.

## Required Behavior
- Reader phai uu tien doc du lieu truc tiep tu app thong qua UI hierarchy dump.
- Neu hierarchy dump khong expose du thong tin, reader chi duoc chuyen sang runtime-accessible source that:
  - app log trong shared storage
  - local save/cache trong shared storage
- Neu khong tim thay source that, phai tra ve chan doan ro rang:
  - `UNSUPPORTED_RENDER_SURFACE`
  - `TRUE_PARAMETER_SOURCE_NOT_FOUND`
- Tuyet doi khong tu dong fallback sang screenshot reader hoac OCR.

## Safety
- Project nay doc lap voi pipeline OCR hien tai.
- Khong sua `backend/core/ocr_engine.py`, `backend/tasks/task_queue.py`, DB schema, hay API scan cu trong V1.
