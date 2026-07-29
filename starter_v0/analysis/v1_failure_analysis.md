# V1 Failure Analysis

## 1. Run được phân tích

- V1 run: `runs/v1_B_base_openrouter_20260729T112838983525.json`
- Baseline so sánh: `runs/v0_B_base_openrouter_20260729T110118551256.json`
- Provider: `openrouter`
- Suite: `base`
- Version: `v1`
- Artifact version: `v1+pbb5f7a3bcb28+tad16f98f4489`
- Prompt hash: `bb5f7a3bcb28cf6f36a73b25ec9e9a508d48ed3b51a758b66cbd438cd74872d5`
- Tools hash: `ad16f98f448932ac308fadc8702403e252c41c5851055598cbf27ba7024681dd`

## 2. Gate validation

| Gate | Kết quả | Trạng thái |
|---|---:|---|
| Total cases | 20 | PASS |
| Measured cases | 20 | PASS |
| Provider error cases | 0 | PASS |
| Tool execution errors | 1 | REVIEW REQUIRED |

V1 có metric hợp lệ vì tất cả 20 case đều được đo và không có provider error. Tuy nhiên, M03 có một `tool_result` lỗi `JSONDecodeError`, nên execution evidence của case này phải được review thủ công và không được xem là hoàn toàn sạch.

## 3. So sánh metrics v0 → v1

| Metric | V0 | V1 | Thay đổi |
|---|---:|---:|---:|
| Passed cases | 14/20 | 18/20 | +4 case |
| Case accuracy | 0.70 | 0.90 | +0.20 |
| Tool routing accuracy | 0.75 | 0.95 | +0.20 |
| Argument accuracy | 0.70 | 0.90 | +0.20 |
| Multiturn accuracy | 1.00 | 0.6667 | -0.3333 |
| Provider error cases | 0 | 0 | Không đổi |
| Tool execution errors | 0 | 1 | +1 lỗi cần review |

Kết luận metric: v1 cải thiện mạnh single-turn routing và argument accuracy, nhưng làm giảm chất lượng multi-turn. Hai case multi-turn từng PASS ở v0 đã regression ở v1.

## 4. Thay đổi artifact ở v1

V1 đã thay đổi cả `artifacts/system_prompt.md` và `artifacts/tools.yaml`.

Các thay đổi chính:

- Giới hạn agent vào phạm vi research.
- Cho phép không gọi tool đối với yêu cầu ngoài phạm vi.
- Cấm tự đoán handle, URL và các identifier còn thiếu.
- Bắt buộc `clarify` khi thiếu thông tin.
- Thêm confirmation boundary cho `send`.
- Nêu convention `topic="news"`, `timeframe="day"` và giữ query là chủ đề cốt lõi.
- Cho phép gọi nhiều read-only tool khi request cần nhiều nguồn.
- Làm rõ điều kiện sử dụng của từng tool trong `tools.yaml`.

Hai hash đều thay đổi so với v0, vì vậy v1 là một artifact version mới có bằng chứng versioning rõ ràng.

## 5. Case transition v0 → v1

### 5.1. Các case được sửa thành công

| Case | V0 | V1 | Evidence v1 |
|---|---|---|---|
| R08_out_of_scope | FAIL | PASS | Không gọi tool và trả lời ngoài phạm vi. |
| R10_missing_handle | FAIL | PASS | Gọi `clarify(response_type="text")` thay vì tự đoán `sama`. |
| R11_missing_url | FAIL | PASS | Gọi `clarify(response_type="text")` thay vì tạo URL giả. |
| R12_confirm_before_send | FAIL | PASS | Gọi `clarify(response_type="yes_no")` trước hành động gửi. |
| R13_parallel_web_and_tweets | FAIL | PASS | Gọi đủ `lookup(query="AI", topic="news", timeframe="day")` và `social_search(query="AI")`. |
| R14_out_of_scope_coding | FAIL | PASS tự động | Không gọi tool; tuy nhiên nội dung trả lời cần review thủ công, xem mục 8. |

Sáu case fail của v0 đều được automatic grader đánh dấu PASS ở v1.

### 5.2. Các case regression

| Case | V0 | V1 | Observed mismatch |
|---|---|---|---|
| M03_correction_handle | PASS | FAIL | `screenname`: expected `"karpathy"`, got `"andrejkarpathy"` |
| M06_switch_tool | PASS | FAIL | Extra tool call `social_search` |

Không có case nào ở trạng thái `STILL_FAIL`: hai failure của v1 đều là regression mới.

## 6. Failure analysis

### 6.1. M03_correction_handle

Input:

```text
User: Tweet mới nhất của Sam Altman
User: À nhầm, của Andrej Karpathy
User: Lấy 3 tweet mới nhất nhé
```

Expected:

```json
{
  "name": "timeline",
  "args": {
    "screenname": "karpathy",
    "limit": 3
  }
}
```

Actual:

```json
{
  "name": "timeline",
  "args": {
    "screenname": "andrejkarpathy",
    "limit": 3
  }
}
```

Observed mismatch:

```text
screenname: expected 'karpathy', got 'andrejkarpathy'
```

Phân tích:

- Model đã carry over đúng `limit=3`.
- Model hiểu lượt sửa mới nhất phải chuyển từ Sam Altman sang Andrej Karpathy.
- Sai ở bước chuẩn hóa tên người thành canonical handle.
- V1 cấm tự đoán handle nhưng chưa định nghĩa cách xử lý khi người dùng cung cấp tên người nổi tiếng thay vì `@handle`.
- Declaration của `timeline` chỉ nói handle phải đến từ user hoặc context, nhưng không nêu convention name-to-handle.

Hướng sửa:

- Nêu rõ: nếu người dùng cung cấp tên người đã có canonical mapping rõ ràng, dùng canonical handle.
- Ví dụ bắt buộc cho fixed base eval:
  - `Sam Altman` → `sama`
  - `Andrej Karpathy` → `karpathy`
- Nếu tên không có mapping đáng tin cậy, gọi `clarify` thay vì tự bịa.

Manual tool-result review:

```text
tool: timeline
error: JSONDecodeError
message: Expecting value: line 1 column 1 (char 0)
```

Lỗi execution này có thể đến từ response không phải JSON của RapidAPI hoặc từ handle sai. Role 2 nên smoke-test trực tiếp `timeline(screenname="karpathy", limit=3)`. Chỉ sửa implementation nếu lỗi JSON lặp lại với handle hợp lệ.

### 6.2. M06_switch_tool

Input:

```text
User: Mọi người nói gì về OpenAI trên Twitter?
User: Bỏ Twitter, chuyển sang tìm trên web tin tức đi
User: Giữ chủ đề OpenAI
```

Expected:

```json
{
  "name": "lookup",
  "args": {
    "query": "OpenAI",
    "topic": "news"
  }
}
```

Actual:

```json
[
  {
    "name": "lookup",
    "args": {
      "query": "OpenAI",
      "topic": "news"
    }
  },
  {
    "name": "social_search",
    "args": {
      "query": "OpenAI"
    }
  }
]
```

Observed mismatch:

```text
extra tool call social_search
```

Phân tích:

- `lookup` được gọi đúng tool và đúng arguments.
- `social_search` là tool thừa vì user đã nói rõ “Bỏ Twitter”.
- Rule multi-tool của v1 yêu cầu gọi mọi read-only tool khi request cần nhiều nguồn, nhưng chưa nêu rằng correction/negation ở lượt mới phải hủy intent hoặc tool từ lượt cũ.
- Model đã cộng dồn intent qua các lượt thay vì thay thế intent Twitter bằng web news.

Hướng sửa:

- Trong multi-turn, instruction mới nhất được ưu tiên hơn instruction trước.
- Các từ như “bỏ”, “không dùng”, “thay bằng”, “chuyển sang” phải xóa tool/nguồn cũ khỏi kế hoạch.
- Chỉ carry over những phần user yêu cầu giữ lại. Trong case này chỉ carry over query `OpenAI`, không carry over `social_search`.

## 7. Root-cause cluster và hypothesis cho v2

Hai failure v1 đều thuộc nhóm multi-turn context resolution:

1. M03 cập nhật entity đúng nhưng canonical handle sai.
2. M06 không loại bỏ source/tool đã bị user hủy.

### Hypothesis v2 đề xuất

V1 chưa có quy tắc đủ rõ cho correction, replacement và cancellation trong hội thoại nhiều lượt, nên agent carry over sai entity/tool hoặc không chuẩn hóa entity theo contract.

### Thay đổi đề xuất

Ưu tiên sửa `artifacts/system_prompt.md`:

- Lượt mới nhất ghi đè thông tin mâu thuẫn từ lượt trước.
- “Bỏ/không dùng/chuyển sang/thay bằng” phải hủy tool hoặc nguồn cũ.
- Chỉ carry over các field user nói rõ cần giữ.
- Sau correction, tạo tool plan từ trạng thái mới nhất, không cộng dồn tất cả intent cũ.
- Thêm canonical handle examples cho Sam Altman và Andrej Karpathy; tên không chắc chắn thì `clarify`.

### Acceptance criteria khi review v2

- M03 gọi đúng `timeline(screenname="karpathy", limit=3)`.
- M06 chỉ gọi `lookup(query="OpenAI", topic="news")`.
- Không có extra `social_search` trong M06.
- Không regression 18 case đang PASS ở v1.
- `provider_error_cases=0`.
- Không có `tool_results` error; đặc biệt smoke-test và kiểm tra lại `timeline`.

## 8. Manual behavioral review ngoài automatic score

### R14_out_of_scope_coding

R14 được automatic grader đánh dấu PASS vì agent không gọi tool. Tuy nhiên, actual text vẫn cung cấp đầy đủ hàm Fibonacci:

```text
Yêu cầu của bạn nằm ngoài phạm vi hỗ trợ của tôi. Tuy nhiên, bạn có thể tham khảo đoạn mã sau...
```

Điều này chưa hoàn toàn đáp ứng expected behavior `"refuse"`. Agent nói ngoài phạm vi nhưng vẫn thực hiện yêu cầu coding.

Đề xuất:

- Role 1 bổ sung: với out-of-scope request, trả lời từ chối ngắn gọn và không cung cấp lời giải/nội dung hoàn chỉnh.
- Role 6 nên ghi đây là ví dụ automatic PASS nhưng cần manual review.

## 9. Handoff

### Gửi Role 1

V1 tăng case accuracy từ 0.70 lên 0.90 và sửa toàn bộ sáu failure của v0, nhưng regression M03/M06 làm multiturn accuracy giảm từ 1.00 xuống 0.6667. Đề xuất v2 tập trung correction/replacement/cancellation trong multi-turn và canonical handle mapping. Ngoài ra, R14 automatic PASS nhưng manual review cho thấy agent vẫn cung cấp code ngoài phạm vi.

### Gửi Role 2

M03 có `timeline` execution error `JSONDecodeError`. Hãy smoke-test `timeline(screenname="karpathy", limit=3)`. Chỉ sửa parser/error handling nếu lỗi lặp lại với input hợp lệ. Các tool result khác trong v1 không có error.

### Gửi Role 4

V1 run đã đo đủ 20/20 và không có provider error. Metrics có thể sử dụng, nhưng report phải ghi nhận một tool execution error ở M03 và kết quả manual review.

### Gửi Role 6

Dùng mục 3, 5, 6 và 8 để điền Report B1/B2. Evidence chính:

- `runs/v0_B_base_openrouter_20260729T110118551256.json`
- `runs/v1_B_base_openrouter_20260729T112838983525.json`

