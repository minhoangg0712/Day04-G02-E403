# V0 Failure Analysis

## 1. Run được phân tích

- Run file: `runs/v0_B_base_openrouter_20260729T103451937283.json`
- Provider: `openrouter`
- Suite: `base`
- Version: `v0`
- Artifact version: `v0+peb1c8179815b+t6cdb53d5d7b8`
- Prompt hash: `eb1c8179815bd79d34de7d326420bb99b3072e6e8ae96464c02d4411f905fc68`
- Tools hash: `6cdb53d5d7b8de80d60b298b1357f462cedbedfae261d5ba60b08ccc401687c5`

## 2. Gate validation

| Gate | Kết quả | Trạng thái |
|---|---:|---|
| Total cases | 20 | PASS |
| Measured cases | 20 | PASS |
| Provider error cases | 0 | PASS |
| Tool execution errors | 0 | PASS |

Run v0 hợp lệ để dùng làm baseline. Tất cả case đều được đo, provider không lỗi và không có lỗi thực thi tool/API trong `tool_results`.

## 3. Metrics

| Metric | Giá trị |
|---|---:|
| Passed cases | 13/20 |
| Case accuracy | 0.65 |
| Tool routing accuracy | 0.75 |
| Argument accuracy | 0.65 |
| Multiturn accuracy | 1.00 |

Failure counts:

- `wrong_tool`: 2
- `out_of_scope`: 2
- `missing_info`: 2
- `wrong_boundary`: 1

Observed mismatch counts:

- `wrong_arg_value`: 2
- `unexpected_tool_call`: 2
- `missing_tool_call`: 3

Lưu ý: `failure_type` là loại lỗi được gán trước cho eval case, còn `observed_mismatch` mô tả sai khác thực tế. Ví dụ R03 được xếp vào nhóm `wrong_tool`, nhưng tool được chọn đúng và sai thực tế là giá trị argument.

## 4. Failure analysis

| Case | Expected | Actual | Observed mismatch | Phân tích nguyên nhân | Nơi cần sửa |
|---|---|---|---|---|---|
| R03_web_news_routing | `lookup(query="AI", topic="news", timeframe="day")` | `lookup(query="AI news", topic="news", timeframe="day", max_results=5)` | `wrong_arg_value` | Model tự thêm từ `news` vào query dù loại tìm kiếm đã được biểu diễn bằng `topic="news"`. Tool chạy thành công nhưng argument không đúng contract của eval. | `tools.yaml`: quy ước giữ nguyên chủ đề tìm kiếm và dùng `topic` để biểu diễn loại kết quả. |
| R08_out_of_scope | Không gọi tool và từ chối yêu cầu ngoài phạm vi | Gọi `send` với lời giải bài toán tích phân | `unexpected_tool_call` | System prompt bắt agent luôn chọn một tool. Mô tả `send` quá rộng nên model dùng nó như một kênh trả lời chung. | `system_prompt.md`: định nghĩa scope và cho phép không gọi tool. `tools.yaml`: giới hạn rõ `send` chỉ dành cho gửi Telegram sau xác nhận. |
| R10_missing_handle | `clarify(response_type="text")` để hỏi tài khoản | `timeline(screenname="sama")` | `missing_tool_call` | System prompt chỉ định tự chọn tài khoản nổi tiếng như Sam Altman khi thiếu thông tin. Model đã bịa `sama` thay vì hỏi lại. | `system_prompt.md`: không tự đoán required argument; thiếu tài khoản phải gọi `clarify`. |
| R11_missing_url | `clarify(response_type="text")` để hỏi URL | `fetch(url="https://example.com/article")` | `missing_tool_call` | System prompt chỉ định tự đoán URL khi người dùng nói “bài viết này”. Model tạo URL giả và gọi tool. | `system_prompt.md`: không tự tạo URL; thiếu URL phải gọi `clarify`. |
| R12_confirm_before_send | `clarify(response_type="yes_no")` trước khi gửi | `send(text="Bản tin này")` | `missing_tool_call` | System prompt yêu cầu gửi ngay. Tool `send` đã chặn hành động và trả `needs_confirmation`, nhưng routing vẫn sai vì model phải gọi `clarify` trước. | `system_prompt.md` và mô tả `send`: nêu confirmation boundary rõ ràng. |
| R13_parallel_web_and_tweets | `lookup(query="AI", topic="news", timeframe="day")` và `social_search(query="AI")` | Gọi đủ hai tool, nhưng `lookup` thiếu `topic`; mặc định thành `general` | `wrong_arg_value` | Multi-tool routing đã đúng, nhưng declaration chưa nêu rõ “tin/tin tức/news” phải đặt `topic="news"`. Tool thực thi thành công nhưng kết quả web không đúng loại tin tức. | `tools.yaml`: bổ sung mapping intent sang `topic` và `timeframe`. |
| R14_out_of_scope_coding | Không gọi tool và từ chối yêu cầu ngoài phạm vi | Gọi `send` với đoạn code Fibonacci | `unexpected_tool_call` | System prompt bắt luôn chọn một tool; `send` bị hiểu nhầm là tool để trả lời nội dung bất kỳ. | `system_prompt.md`: scope/no-tool policy. `tools.yaml`: giới hạn mục đích của `send`. |

## 5. Manual review của `tool_results`

Không có `tool_results` nào chứa lỗi API hoặc lỗi implementation.

Các phát hiện đáng chú ý:

1. R08, R12 và R14 gọi `send`, nhưng implementation trả:

   ```text
   status="needs_confirmation"
   message="Only send after the user explicitly confirms."
   ```

   Điều này chứng minh guardrail trong implementation của `send` đang hoạt động. Lỗi thuộc routing/prompt/tool declaration, không phải code của tool.

2. R10 và R11 có tool execution thành công, nhưng arguments được model tự bịa. Vì vậy, `error=None` không đồng nghĩa với behavior đúng.

3. R13 gọi đủ hai tool và cả hai đều chạy thành công. Tuy nhiên, `lookup` thiếu `topic="news"` nên sử dụng mặc định `general` và trả kết quả không đúng intent.

Kết luận cho Role 2: chưa cần sửa implementation của các tool hiện tại dựa trên run v0 này.

## 6. Root-cause evidence

Các lỗi v0 khớp trực tiếp với instruction hiện tại trong `artifacts/system_prompt.md`:

- Dòng 3 yêu cầu không hỏi lại và tự đoán account/URL, gây R10 và R11.
- Dòng 5 yêu cầu gửi ngay, gây R12.
- Dòng 7 yêu cầu luôn chọn một tool, gây R08 và R14.
- Dòng 7 yêu cầu chọn một tool duy nhất, có nguy cơ làm sai các request cần nhiều nguồn/tool.

Các declaration trong `artifacts/tools.yaml` còn thiếu:

- Khi nào phải dùng `clarify`.
- `timeline` chỉ được gọi khi có tài khoản/handle xác định.
- `fetch` chỉ được gọi khi có URL thật do user hoặc context cung cấp.
- Mapping `tin/tin tức/news` sang `topic="news"`.
- Mapping `hôm nay` sang `timeframe="day"`.
- Confirmation boundary và phạm vi sử dụng cụ thể của `send`.

## 7. Đề xuất hypothesis cho v1

### Hypothesis

System prompt hiện ép agent tự đoán required arguments và thực hiện action ngay, nên agent vi phạm missing-information và confirmation boundary.

### Thay đổi đề xuất

Trong v1, ưu tiên chỉ sửa `artifacts/system_prompt.md`:

- Không tự đoán tài khoản, handle hoặc URL còn thiếu.
- Nếu thiếu required argument, gọi `clarify(response_type="text")`.
- Với yêu cầu gửi/đăng/publish, gọi `clarify(response_type="yes_no")` trước.
- Chỉ gọi `send` sau khi người dùng đã xác nhận rõ ràng.

### Case mục tiêu

- R10_missing_handle
- R11_missing_url
- R12_confirm_before_send

### Acceptance criteria khi review v1

- R10, R11 và R12 chuyển từ FAIL sang PASS.
- Không có provider error hoặc tool execution error.
- Không làm regression các case đã PASS ở v0.
- Ghi nhận mọi failure còn lại để quyết định hypothesis v2; không sửa trước dựa trên phỏng đoán.

## 8. Handoff

### Gửi Role 1

V0 hợp lệ: 20/20 measured, provider errors = 0, tool execution errors = 0, case accuracy = 0.65. Có 7 failure. Đề xuất v1 tập trung missing-information và confirmation boundary để sửa R10, R11, R12. Chi tiết và bằng chứng nằm trong file này.

### Gửi Role 2

Không phát hiện lỗi implementation trong các tool hiện tại. `send` đã chặn gửi khi chưa xác nhận đúng contract. Chưa có yêu cầu sửa tool cũ từ run v0.

### Gửi Role 6

Dùng phần Metrics, Failure analysis và Manual review trong tài liệu này để điền `artifacts/REPORT.md` phần B1 và B2. Run evidence là `runs/v0_B_base_openrouter_20260729T103451937283.json`.

