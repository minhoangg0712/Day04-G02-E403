# Day 04 Lab v2 Report — Research Agent

## Team

- **Team:** Day04-G02-E403
- **Members:** Nguyễn Minh Hoàng - 2A202601609;
Nguyễn Duy Lâm - 2A202601073;
Lê Ngọc Khánh - 2A202601487;
Nguyễn Tuấn Anh - 2A202601775;
Lê Mạnh Cương - 2A202601137;
Vũ Ngọc Thiện - 2A202601793.
- **Provider / model đã chạy eval:** OpenRouter / `openai/gpt-4o-mini`
- **UI:** Streamlit (`app.py`)
- **Chạy local:** `streamlit run app.py`
- **Demo URL local:** `http://localhost:8501`
- **Public deployment/tunnel:** Chưa có

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Nhóm xây dựng một **Research Agent** có khả năng định tuyến yêu cầu người dùng đến tool phù hợp để tìm kiếm web/news, tìm social posts, đọc URL, tra cứu company policy, tìm paper arXiv và định dạng kết quả.

CLI, evaluation và UI dùng chung `artifacts/system_prompt.md`, `artifacts/tools.yaml` và `run_model_tool_loop` trong `chat.py`. Streamlit UI hiển thị request/response, tool trace gồm tên tool, arguments, result/error và lưu transcript JSON.

Agent không được tự đoán URL, handle hoặc destination còn thiếu. Với yêu cầu gửi/publish, agent phải yêu cầu xác nhận rõ ràng trước khi gọi action tool.

## A2. Tool agent có

| Tool | Chức năng | Trạng thái |
|---|---|---|
| `clarify` | Hỏi một câu làm rõ khi thiếu thông tin hoặc cần xác nhận hành động. | Core |
| `timeline` | Lấy bài đăng gần đây từ một social account có handle rõ ràng. | Core |
| `social_search` | Tìm social posts theo từ khóa/chủ đề. | Core |
| `lookup` | Tìm web/news; hỗ trợ `topic="news"` và `timeframe="day"`. | Core |
| `fetch` | Đọc nội dung từ URL được cung cấp rõ ràng. | Core |
| `format` | Định dạng các items đã có thành markdown digest. | Core |
| `send` | Gửi text ra ngoài sau explicit confirmation. | Optional built-in |
| `policy` | Tìm trong company policy nội bộ. | Optional built-in |
| `papers` | Tìm paper trên arXiv. | Optional built-in |
| `paper_text` | Trích text từ arXiv paper ID/URL. | Optional built-in |
| `extract_keywords` | Trích keyword theo tần suất từ text đã có. | Tool mới, chưa tích hợp hoàn chỉnh |

### Trạng thái tool mới `extract_keywords`

Nhóm đã có implementation và tài liệu tại:

- `tools/extract_keywords/tool.py`
- `tools/extract_keywords/TOOL.md`

Tool nhận `text`, `max_keywords`, `min_length` và trả về `keywords`, `keyword_count`, `token_count`. Tuy nhiên, tool hiện chưa được import/đăng ký trong `tools/__init__.py` và chưa có declaration trong `artifacts/tools.yaml`. Vì vậy, tool chưa thể được tính là tool mới hoàn thành cho yêu cầu lab.

## A3. Câu hỏi mẫu để thử

1. `Tìm tin AI hôm nay và tóm tắt các nguồn chính.`
2. `Mọi người nói gì về OpenAI trên Twitter?`
3. `Đọc và tóm tắt https://example.com`
4. `Tìm 2 paper arXiv về AI agent evaluation.`
5. `Gửi bản tin này lên Telegram.`

Với câu 5, kỳ vọng agent gọi `clarify(response_type="yes_no")` thay vì gửi ngay.

## A4. Kịch bản demo đã rehearse / cần rehearse

| Scenario | Tool trace kỳ vọng | Câu chuyện evidence |
|---|---|---|
| Tin AI hôm nay | `lookup(query="AI", topic="news", timeframe="day")` | v0 sai arguments; v1 bổ sung quy ước routing news. |
| Thiếu handle | `clarify(response_type="text")` | v0 tự đoán `sama`; v1 chuyển sang hỏi người dùng. |
| Thiếu URL | `clarify(response_type="text")` | v0 tự tạo URL; v1 chỉ fetch URL được cung cấp. |
| Gửi khi chưa xác nhận | `clarify(response_type="yes_no")` | v0 gọi `send` trực tiếp; v1 đã tuân thủ confirmation boundary. |
| Chuyển từ Twitter sang web news | Chỉ `lookup(query="OpenAI", topic="news")` | v1 vẫn gọi thừa `social_search`; đây là limitation cần sửa ở v2. |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

Hai run hiện có đều có `total_cases = 20`, `measured_cases = 20` và `provider_error_cases = 0`; do đó các metric routing dưới đây có thể dùng để so sánh.

| Version | Prompt/tool change | Hypothesis | Case accuracy | Tool routing | Argument | Multiturn | Run file |
|---|---|---|---:|---:|---:|---:|---|
| v0 | Baseline. | Chưa tối ưu. | 0.70 (14/20) | 0.75 | 0.70 | 1.00 | `runs/v0_B_base_openrouter_20260729T110118551256.json` |
| v1 | Thêm scope/no-tool policy, cấm đoán URL/handle, confirmation boundary, quy ước news arguments và multi-tool routing. | Prompt và tool descriptions rõ hơn sẽ sửa lỗi missing information, action boundary và out-of-scope của v0. | 0.90 (18/20) | 0.95 | 0.90 | 0.6667 | `runs/v1_B_base_openrouter_20260729T112838983525.json` |
| v2 | Thêm canonical handle mapping và quy tắc latest-turn-wins; các từ “bỏ/chuyển sang/skip” hủy source/tool cũ. | Quy tắc rõ ràng cho correction và cancellation sẽ sửa M03/M06 mà không làm regression các case đã pass. | 1.00 (20/20) | 1.00 | 1.00 | 1.00 | `runs/v2_B_base_openrouter_20260729T124517273558.json` |
| v3 | Chưa chạy. | Chưa có evidence. | — | — | — | — | — |

### Artifact versions

| Version | Artifact version | Prompt hash | Tools hash |
|---|---|---|---|
| v0 | `v0+peb1c8179815b+t6cdb53d5d7b8` | `eb1c8179815b...` | `6cdb53d5d7b8...` |
| v1 | `v1+pbb5f7a3bcb28+tad16f98f4489` | `bb5f7a3bcb28...` | `ad16f98f4489...` |
| v2 | `v2+p85aa5bd8fca4+t631b2950896f` | `85aa5bd8fca4...` | `631b2950896f...` |

### Kết quả chính

- v1 tăng **case accuracy từ 0.70 lên 0.90**, tương đương tăng 4 case pass.
- Tool routing accuracy tăng từ `0.75` lên `0.95`.
- Argument accuracy tăng từ `0.70` lên `0.90`.
- Sáu lỗi v0 được automatic grader đánh dấu PASS ở v1.
- Multiturn accuracy giảm từ `1.00` xuống `0.6667` do hai regression multi-turn.
- V2 sửa cả hai regression multi-turn của v1: M03 dùng canonical handle `karpathy`; M06 chỉ giữ `lookup` sau khi user bỏ Twitter. V2 đạt **20/20 PASS** và tất cả metric bằng `1.00`.
- V2 có `provider_error_cases=0`, không có observed mismatch và không có `tool_results.error` trong run JSON.
- `artifacts/version_log.csv` đã có dòng v2; cần bổ sung v0, v1 và v3 trước khi nộp bài.

## B2. Failure analysis

| Run / case | Actual tool call | What failed | Root cause | Hướng xử lý |
|---|---|---|---|---|
| v0 — out-of-scope | `send(...)` | Agent gọi tool cho bài tích phân/code Fibonacci. | Prompt baseline ép agent luôn chọn một tool; `send` bị hiểu quá rộng. | Giữ scope/no-tool policy; kiểm tra agent từ chối thay vì vẫn trả lời nội dung ngoài scope. |
| v0 — missing handle | `timeline(screenname="sama")` | Thiếu `clarify`; model tự đoán account. | Prompt baseline cho phép tự đoán account nổi tiếng. | V1 cấm đoán identifier bắt buộc. |
| v0 — missing URL | `fetch(url="https://example.com/article")` | Thiếu `clarify`; model tạo URL giả. | Prompt baseline cho phép tự đoán URL. | V1 chỉ gọi `fetch` khi có URL rõ ràng. |
| v0 — send boundary | `send(text="Bản tin này")` | Không hỏi confirmation trước. | Prompt yêu cầu gửi ngay. | V1 yêu cầu `clarify(response_type="yes_no")` trước action. |
| v0 — web/news arguments | `lookup(query="AI news", timeframe="day")` | Query sai và thiếu `topic="news"`. | Chưa quy định mapping news intent sang tool arguments. | V1 dùng core topic `AI`, `topic="news"`, `timeframe="day"`. |
| v1 — M03 correction handle | `timeline(screenname="andrejkarpathy", limit=3)` | Expected `screenname="karpathy"`. | Agent cập nhật entity đúng nhưng chưa chuẩn hóa canonical handle. | v2 thêm mapping `Andrej Karpathy → karpathy`; smoke test tool. |
| v1 — M06 switch source | `lookup(...)` + `social_search(...)` | `social_search` là extra tool sau khi user nói “Bỏ Twitter”. | Prompt chưa ưu tiên cancellation/replacement ở lượt mới. | v2: latest turn overrides prior source/tool. |
| v2 — M03 correction handle | `timeline(screenname="karpathy", limit=3)` | PASS. | Canonical mapping `Andrej Karpathy → karpathy` được nêu rõ trong prompt/declaration. | Giữ mapping; tên không có mapping đáng tin cậy phải gọi `clarify`. |
| v2 — M06 switch source | `lookup(query="OpenAI", topic="news")` | PASS; không còn `social_search` thừa. | Prompt ưu tiên instruction mới nhất và hủy source/tool mà user yêu cầu bỏ. | Giữ quy tắc latest-turn-wins và cancellation. |

### Manual review

1. Theo `analysis/v1_failure_analysis.md`, M03 từng có một tool-result lỗi `JSONDecodeError`. Trong v2, toàn bộ 20 case PASS và run JSON không có `tool_results.error`; tuy vậy vẫn nên smoke test `timeline(screenname="karpathy", limit=3)` trước demo để kiểm tra quota/API live.
2. R14 được automatic grader tính PASS vì agent không gọi tool, nhưng phần text vẫn đưa ra code Fibonacci. Đây chưa phải từ chối out-of-scope hoàn toàn.
3. Tool result không lỗi không đồng nghĩa routing/arguments đúng: v0 có các tool chạy được nhưng URL, handle hoặc intent vẫn sai.

## B3. Team eval cases

`data/eval_group.json` hiện có `cases: []`, tức là **chưa có team-authored eval case**.

Yêu cầu bắt buộc của lab:

- 5 single-turn cases dùng `query`;
- 5 multi-turn cases dùng `turns`;
- tổng cộng đúng 10 case;
- mỗi case có `id`, `phase="B"`, `failure_type`, `expect`, `metadata.what_it_tests`.

| Hạng mục | Trạng thái | Việc cần làm |
|---|---|---|
| 5 single-turn | Chưa có | Viết 5 case. |
| 5 multi-turn | Chưa có | Viết 5 case; user turn cuối là turn được chấm. |
| Group eval | Chưa chạy | Chạy `run_eval.py` sau khi hoàn thiện 10 cases. |

Các chủ đề nên có trong team eval: thiếu URL/handle, action confirmation, out-of-scope/no-tool, chuyển nguồn trong multi-turn, canonical handle, web-news arguments, và `extract_keywords` sau khi tool được tích hợp.

## B4. Live chat / UI evidence

`app.py` đã có Streamlit UI với các chức năng:

- load environment từ `.env` bằng `load_lab_env(ROOT)`;
- dùng chung `run_model_tool_loop` với `chat.py`;
- chọn provider, model, artifact version, history window và max tool rounds;
- hiển thị request/response;
- hiển thị tool calls, arguments, outputs và errors;
- lưu transcript JSON bằng `write_transcript`.

Tại thời điểm viết báo cáo, thư mục `transcripts/` chưa có transcript thực tế. Vì vậy, nhóm chưa thể claim live UI evidence đã hoàn thành.

Chạy UI:

```powershell
cd starter_v0
streamlit run app.py
```

Sau đó chạy và lưu tối thiểu ba tình huống: một research request bình thường, một request thiếu thông tin rồi user bổ sung ở lượt sau, và một action yêu cầu confirmation.

| Scenario / turn | Version | Tool calls + args | Transcript | Outcome |
|---|---|---|---|---|
| Chưa có evidence | — | — | — | Chưa chạy / chưa lưu transcript |

## B5. Tool capability evidence

| Category | Evidence file | What worked | Risk / guardrail |
|---|---|---|---|
| Core built-ins | `artifacts/tools.yaml`, `tools/__init__.py`, v0/v1 runs | v1 routing accuracy đạt `0.95`. | Smoke test các API tool nhóm thực sự dùng. |
| Must-have: tool mới đầu tiên | `tools/extract_keywords/TOOL.md`, `tools/extract_keywords/tool.py` | Implementation và contract đã tồn tại. | Chưa registry/YAML/quicktest nên chưa hoàn thành. |
| Action tool | `tools/send/tool.py` | `confirmed=False` trả `status="needs_confirmation"`. | Không live-send trong eval; chỉ gửi private demo channel sau explicit confirmation. |
| UI core deliverable | `app.py`, `requirements.txt` | Streamlit đã được thêm vào requirements; code có trace/transcript path. | Cần UI smoke test và transcript thật. |

### Quicktest cho `extract_keywords`

Sau khi import tool vào `tools/__init__.py`, đăng ký trong `TOOL_FUNCTIONS` và khai báo YAML:

```powershell
python -c "from pathlib import Path; from env_loader import load_lab_env; load_lab_env(Path.cwd()); from tools import TOOL_FUNCTIONS as T; r=T['extract_keywords'](text='AI agent evaluation evaluates AI agents', max_keywords=3); print({'error': r.get('error'), 'keywords': r.get('keywords')})"
```

PASS khi registry tìm thấy tool, `error` là `None`, và kết quả có keyword hợp lệ.

## B6. Reflection và next steps

### Phân chia thay đổi giữa prompt và tool declaration

**Nên đặt trong `system_prompt.md`:**

- scope/no-tool policy;
- không tự đoán required identifiers;
- confirmation boundary;
- latest-turn-wins trong multi-turn;
- quy tắc correction/replacement/cancellation;
- canonical handle mappings.

**Nên đặt trong `tools.yaml`:**

- mô tả khi nào dùng/không dùng từng tool;
- argument convention cho `lookup`;
- giới hạn `send` là write/action tool;
- schema đầy đủ của `extract_keywords`.

### Việc phải hoàn thành trước khi nộp

1. Bảo đảm `.env` và API key không bị commit; chỉ để placeholder trong `.env.example`.
2. Hoàn tất tích hợp `extract_keywords` vào registry và `tools.yaml`, rồi chạy quicktest.
3. Smoke test provider và các core tool nhóm sử dụng.
4. Kiểm tra lỗi `timeline` / `JSONDecodeError` ở M03.
5. Viết đúng 10 group eval cases và chạy group eval.
6. Chạy v3 với hypothesis riêng, sau đó cập nhật `version_log.csv`. V2 đã chạy và đạt 20/20 PASS.
7. Chạy Streamlit UI, rehearse demo và lưu transcript thật.
8. Cập nhật tên nhóm, thành viên, link demo và evidence còn thiếu.

### Kết quả v2 và hướng cải thiện v3

V2 đã triển khai và kiểm chứng các quy tắc multi-turn context resolution:

- lượt mới nhất ghi đè thông tin mâu thuẫn;
- “bỏ”, “không dùng”, “chuyển sang”, “thay bằng” phải xóa source/tool cũ khỏi plan;
- chỉ giữ lại các phần user nói rõ cần giữ;
- dùng canonical mapping như `Sam Altman → sama` và `Andrej Karpathy → karpathy`;
- nếu không có mapping đáng tin cậy, gọi `clarify` thay vì đoán.

Kết quả v2 là 20/20 PASS với case accuracy, tool routing accuracy, argument accuracy và multiturn accuracy đều bằng `1.00`. Vì fixed base eval đã đạt trần, v3 nên được xây dựng từ evidence mới: 10 team-authored group cases, quicktest tool mới `extract_keywords`, UI transcript/live demo, hoặc robustness của external API thay vì thay đổi prompt tùy ý.
