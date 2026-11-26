# Kế hoạch kiểm thử web Agent tự sửa

Tài liệu cho đội tester, cập nhật ngày 18/11/2026. Đọc xong có thể tự chạy một ca và biết cần kiểm tra gì.

> Từ 18/11/2026 web **không còn chạy trên cổng thật**: không mở Chromium, không cần đăng nhập VNeID. Mọi lần chạy lại gọi thẳng
> backend thử với giấy tờ của req, rồi xem trường nào nhận giá trị gì trên form mô phỏng của thủ tục, giống web trace.

## 1. Web này làm gì

Khi một ô điền sai (hoặc một giấy đính kèm vào sai dòng), người dùng nhập mã req và mô tả lỗi. Hệ thống tự làm phần còn lại:

1. Chạy lại đúng req đó 5 lần qua backend thử, OCR mới mỗi lần, để xem lỗi có lặp lại không.
2. Các agent AI phân tích và tranh luận. Một agent trọng tài quyết định.
3. Lỗi do OCR đọc sai thì báo cáo và bỏ qua, vì OCR sai thì code không thể biết chữ đúng.
4. Lỗi do code backend thì lập kế hoạch sửa, **chờ người duyệt kế hoạch**, sửa, chạy test.
5. Test qua thì **dừng chờ người duyệt bản sửa**: đọc patch rồi bấm đồng ý thì mới build backend thử và chạy lại 5 lần để chấm.
6. Đạt cả 5 lần thì giữ bản sửa, đẩy lên nhánh `agent/<mã ca>`. Không đạt thì tự hoàn tác và họp lại, tối đa 3 vòng.

Lỗi nằm ở extension (backend trả đúng mà form không nhận) thì hệ thống chỉ báo cáo: không chạy extension nên không kiểm chứng được bản sửa extension.

Trong suốt ca, người chạy làm hai việc: **duyệt kế hoạch sửa** của trọng tài trước khi agent sửa code, và **duyệt bản sửa** trước khi build.

### Xem kết quả: trường nào nhận giá trị gì

Tab **Kết quả điền** (lượt đính kèm là **Kết quả đính kèm**) của mỗi ca có các đợt: **Lượt gốc (req)**, **Trước khi sửa**, **Sau sửa,
vòng n**. Chọn một lần chạy để xem:

- **Mô phỏng form**: các trường backend trả được đặt vào form đã khai của thủ tục, từng ô ghi đã điền, giá trị mặc định, có giá trị
  nhưng không vào được ô, hoặc trống; ô chọn có danh sách lựa chọn để đối chiếu. Giống tab mô phỏng của web trace.
- **Mô phỏng đính kèm**: bảng thành phần hồ sơ, giấy nào (trang nào của tệp nào) vào dòng nào.
- **So sánh các lần**: trường nào ổn định, trường nào đổi giữa các lần.
- **Output máy chủ**: JSON backend trả.

## 2. Tài nguyên

### Địa chỉ

| Thành phần | Địa chỉ | Ghi chú |
| --- | --- | --- |
| Web Agent tự sửa | http://localhost:12008 (máy khác: http://<ip Tailscale máy chạy>:12008) | Giao diện chính |
| Dịch vụ agent | http://127.0.0.1:12009/agent-api/health | Chỉ mở trên máy chạy, trả `{"ok":true,...}` là sống |
| Backend | http://localhost:12005/healthz | Phải trả `{"ok":true,...}`. Web đăng nhập super_admin qua backend này |
| Backend thử | http://127.0.0.1:12025/healthz | Dịch vụ tự build từ khu làm việc (tag release đang chạy production), mọi lần chạy lại và bản sửa chạy ở đây |
| Web Monitor | http://localhost:12007 | Xem trace của một req |

### Tài khoản

| Tài khoản | Dùng để | Ghi chú |
| --- | --- | --- |
| Tài khoản super_admin | Đăng nhập web Agent tự sửa | Tài khoản khác bị từ chối |
| Tài khoản test theo đơn vị | Không cần nhập | Dịch vụ tự dựng trên backend thử: cùng username, xã, tỉnh với tài khoản đã điền req, mật khẩu ngẫu nhiên chỉ giữ trong RAM |

Tài khoản chỉ tồn tại trong Mongo của từng máy, mật khẩu không ghi trong repo. Máy mới tự tạo theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md).

### Dữ liệu thử

Req lấy từ Mongo nguồn (local, hoặc trolysoao qua SSH chỉ đọc) và kho lưu trữ "Quản lý nội bộ" cho req đã bị dọn. Mỗi lượt agent gửi OCR và ảnh giấy tờ của ca đó lên Anthropic, nên ưu tiên req của tài khoản test. Lấy mã req ở web Monitor hoặc ô "Mã hỗ trợ" của panel extension.

Mã req không ghi trong tài liệu này vì repo public.

Một req vừa được sửa xong, chạy lại với cùng lỗi sẽ ra **Không tái hiện**, dùng được cho kịch bản E4.

Req có thể là lượt **điền** hoặc lượt **đính kèm**; tệp gốc phải còn (trên đĩa hoặc trong kho lưu trữ). Web báo ngay khi nhập mã nếu không đạt.

### Máy chạy

Cần một máy Windows có repo, Docker Desktop, Python 3.11, Node, Claude Code đã đăng nhập và mạng Tailscale tới OCR, LLM. Cài từ đầu theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md). Agent không sửa repo trên máy: mỗi ca nó sửa trong khu làm việc `~/.autotest-hcc/workspace/` (ngoài mọi repo git, clone riêng 3 repo thật, đặt đúng tag release đang chạy production). Ca đầu tiên clone 3 repo, mất vài phút. Bản sửa đạt được đẩy lên nhánh `agent/<mã ca>` của repo thật, có link Mở PR trên web; ca có đụng backend còn để lại một ca hồi quy trong `auto-test-hcc/regression/cases` (soát rồi mới commit).

Người dùng ở máy khác chỉ cần trình duyệt mở web, không phải cài gì.

### Bật hệ thống

Chạy ở gốc repo, lệnh 3 để mở một terminal riêng:

```powershell
# 1. Backend
cd auto-fill-hcc-backend; docker compose -f compose.prod.yml up -d; cd ..

# 2. Web
docker compose -f auto-test-hcc/compose.yml up -d --build

# 3. Dịch vụ agent
python auto-test-hcc/agents/server.py
```

## 3. Cách chạy một ca

1. Mở web, đăng nhập tài khoản super_admin.
2. Nhập mã req. Web hiện tên thủ tục, loại lượt (điền / đính kèm), tài khoản, số tệp.
3. Nhập ô **Lỗi người dùng báo**: ô nào sai, đúng ra phải thế nào.
4. Bấm **Bắt đầu**. Không phải nhập tài khoản chạy lại: dịch vụ tự dựng tài khoản test cùng xã, tỉnh với req.
5. Theo dõi trên web. Duyệt kế hoạch và bản sửa khi web hỏi. Khi xong, đọc kết luận, patch và tab Kết quả điền.

### Ca lỗi đính kèm

1. Lấy **Mã hỗ trợ** extension hiện sau bước đính kèm (khác mã của bước điền). Nhập mã lượt điền thì web gợi ý các mã đính kèm cùng
   hồ sơ, bấm vào mã để tra.
2. Web hiện nhãn **Lượt đính kèm**, số mục, cài đặt Tách giấy tờ lúc đó.
3. Ô **Lỗi người dùng báo** ghi rõ giấy nào vào sai dòng và đúng ra phải vào dòng nào, hoặc trang nào bị sót / bị đính hai lần.
4. Máy chấm kế hoạch backend trả (giấy nào vào dòng nào), không chấm việc tệp có lên cổng không. Bảng kết quả ghi theo dòng:
   `dòng: <tên dòng>` là giấy + trang vào dòng đó, `tệp #n` là từng trang của tệp n vào dòng nào, `tổng: trang thiếu` rỗng là không sót trang.

### Cách xem Dễ hiểu và thủ tục có thanh tra

- Trang ca mặc định ở chế độ **Dễ hiểu**. Khung "Tóm tắt dễ hiểu" ở đầu trang cho biết: lỗi nằm ở bước nào trên sơ đồ (ô viền đỏ
  "Lỗi ở đây"), kết luận bằng lời thường, kết quả điền thử trước / sau khi sửa, và bạn cần làm gì tiếp. Ý kiến chi tiết, file,
  patch, từng bộ test được thu gọn, bấm vào để mở. Muốn xem hết thì bấm **Đầy đủ kỹ thuật**.
- Một số thủ tục có **thanh tra**: sau khi điền lần đầu, một AI khác đọc lại giấy tờ độc lập và chỉ sửa ô khi có bằng chứng trên giấy.
  Ô tra req hiện nhãn "Có thanh tra", sơ đồ có thêm bước "Thanh tra soát lại". Với các thủ tục này, hệ thống chấm trên giá trị
  cuối cùng lên form (sau thanh tra), và hội đồng tự xét lỗi do lần điền đầu hay do thanh tra để sửa đúng một chỗ. Khung kế hoạch
  có dòng "Vì sao sửa ở bước này".

## 4. Luồng chi tiết

| Bước | Ai làm | Trên web thấy gì |
| --- | --- | --- |
| Thu thập chứng cứ từ req | Hệ thống | Giai đoạn Thu thập |
| Chạy lại 5 lần qua backend thử | Hệ thống | Giai đoạn Chạy lại, 5 chấm tròn; tab Kết quả điền có đợt Trước khi sửa |
| Hội đồng phân tích và phản biện | Agent | Các thẻ ý kiến |
| Trọng tài quyết định | Agent | Thẻ Trọng tài |
| Duyệt kế hoạch | **Tester** | Khung vàng "Chờ bạn duyệt kế hoạch sửa": nguyên nhân, kế hoạch, tiêu chí chấm, 3 nút |
| Sửa code backend | Agent | Thẻ Sửa code, patch |
| Test | Hệ thống | Danh sách kiểm tra |
| Duyệt bản sửa | **Tester** | Khung vàng "Chờ bạn duyệt bản sửa": patch, kết quả test, 3 nút |
| Build backend thử | Hệ thống | Dòng Docker trong danh sách kiểm tra |
| Chạy lại 5 lần với bản sửa | Hệ thống | Bảng tiêu chí × lần; tab Kết quả điền có đợt Sau sửa |
| Kết luận | Hệ thống | Khung kết luận |

### Các kết luận

| Kết luận | Ý nghĩa | Code có đổi không |
| --- | --- | --- |
| Đã sửa | Đạt cả 5 lần, không field nào đổi ngoài dự kiến | Có, đẩy lên nhánh `agent/<mã ca>` |
| Bỏ qua: lỗi OCR | Chữ trên giấy khác chữ OCR đọc ra | Không |
| Chỉ báo cáo | Lỗi ở extension, do cổng, giấy tờ thiếu, không phải lỗi, hoặc chưa đủ bằng chứng | Không |
| Không tái hiện | Code hiện tại đã đạt 5/5 | Không |
| Cần người xem | Hết số vòng mà chưa đạt | Có: code của vòng trượt gần nhất để lại cho người xem, chưa build; không dùng thì bấm Hoàn tác bản sửa. Code người duyệt đã bác hoặc lộ dữ liệu thật thì không để lại |
| Không được duyệt | Người duyệt bấm dừng, hoặc quá 60 phút không ai duyệt | Không, đã tự hoàn tác |

### Duyệt kế hoạch sửa

Khi trọng tài quyết định sửa code, khung vàng **Chờ bạn duyệt kế hoạch sửa** hiện ra trước khi agent đụng vào code. Đọc nguyên nhân, các bước, file sẽ sửa và tiêu chí máy sẽ chấm, rồi chọn:

- **Đồng ý, cho sửa**: agent sửa theo đúng kế hoạch.
- **Lập lại kế hoạch theo góp ý**: ghi góp ý (bắt buộc), trọng tài lập kế hoạch mới rồi hỏi lại. Tối đa 3 lần mỗi vòng.
- **Không sửa, dừng**: ca kết thúc ở trạng thái Không được duyệt, chưa có dòng code nào bị đổi.

Quá 60 phút không ai duyệt thì ca tự dừng.

### Duyệt bản sửa

Khi khung vàng **Chờ bạn duyệt bản sửa** hiện, code agent viết đã nằm trong khu làm việc và test đã qua, nhưng chưa build. Đọc patch rồi chọn:

| Nút | Hệ thống làm gì |
| --- | --- |
| Đồng ý, build và chạy kiểm | Build backend thử, chạy lại 5 lần để chấm |
| Không đồng ý, làm lại theo góp ý | Hoàn tác, hội đồng họp lại ở vòng sau và đọc góp ý. Phải ghi góp ý; vòng cuối thì nút này tắt |
| Không đồng ý, dừng | Hoàn tác và kết thúc với kết luận Không được duyệt |

Quá 60 phút không ai bấm thì tự hoàn tác và kết thúc, vì cả hàng đợi đang chờ ca này.

Đạt hay không do máy chấm trên **các trường backend trả** (lượt đính kèm: kế hoạch đính kèm), theo tiêu chí trọng tài đặt.

## 5. Kịch bản kiểm thử

Tình trạng ghi ở cột cuối: **Đạt** là đã chạy và đạt, **Chưa** là chưa chạy lần nào. Tester ưu tiên các dòng Chưa.

### A. Web và phân quyền

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| A1 | Đăng nhập tài khoản không phải super_admin | Thấy câu giải thích, không thấy form | Đạt |
| A2 | Mở form, chưa nhập gì | Nút Bắt đầu tắt | Đạt |
| A3 | Nhập mã req không có | Báo không thấy req | Đạt |
| A4 | Nhập mô tả quá ngắn | Nút Bắt đầu vẫn tắt | Đạt |
| A5 | Không dựng được tài khoản chạy lại (backend thử chưa chạy) | Báo ngay, không tạo ca | Đạt |
| A6 | Tạo ca thứ hai khi ca đầu đang chạy | Ca hai xếp hàng, chạy sau | Đạt |
| A7 | Bấm Dừng khi ca đang chạy lại | Ca dừng ngay | Chưa |
| A8 | Đóng tab web khi ca đang chạy | Ca vẫn chạy, mở lại xem tiếp được | Đạt |
| A9 | Mở web trên khổ điện thoại | Không tràn ngang | Đạt |
| A10 | Tắt dịch vụ agent rồi mở web | Báo chưa chạy và ghi lệnh bật | Đạt |
| A11 | Mở web từ máy khác qua Tailscale | Dùng được đủ, không phải cài gì | Chưa |

### C. Chạy lại và xem trường

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| C1 | Chạy lại 5 lần | 5 mã req khác nhau, "5/5 lần xác nhận OCR mới" | Chưa |
| C2 | Tab Kết quả điền, chọn Lượt gốc (req) | Mô phỏng form khớp giá trị của lượt gốc trên web trace | Chưa |
| C3 | Chọn một lần Trước khi sửa | Mô phỏng form hiện từng ô: đã điền / mặc định / không vào được / trống | Chưa |
| C4 | So sánh các lần | Chỉ ra trường dao động giữa các lần | Chưa |
| C5 | Ca đính kèm, tab Kết quả đính kèm | Bảng thành phần hồ sơ: giấy nào vào dòng nào, cả lượt gốc | Chưa |
| C6 | Ca có sửa | Có thêm đợt Sau sửa, so được với Trước khi sửa | Chưa |

### E. Phân tích và sửa lỗi

| Mã | Tình huống | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| E1 | Lỗi ở BE | Đã sửa, test BE và build chạy, tiêu chí trượt trước sửa thành 5/5 sau sửa | Đạt |
| E2 | Lỗi engine điền ở extension | Chỉ báo cáo, nêu path:dòng cần sửa, không đổi code | Chưa |
| E3 | Lỗi OCR thật | Bỏ qua, nêu trên giấy ghi gì và OCR ra gì, không đổi code | Chưa |
| E4 | Mô tả một lỗi không có thật | Không tái hiện hoặc Chỉ báo cáo, không đổi code | Chưa |
| E5 | Bản sửa trượt | Tự hoàn tác, họp lại với lý do thất bại | Đạt, bằng test tự động |
| E5b | Trượt hết số vòng (Cần người xem) | Code của vòng cuối còn trong khu làm việc, có cảnh báo "CHƯA ĐẠT", backend thử vẫn chạy code gốc, bấm Hoàn tác bản sửa thì về như cũ | Đạt, bằng test tự động |
| E6 | Bấm Hoàn tác bản sửa sau khi xong | File về như cũ, build lại nếu đổi BE | Đạt, bằng test tự động |
| E7 | Bấm Dừng khi agent đang sửa | Code về như cũ | Đạt, bằng test tự động |
| E8 | Bản sửa qua test | Dừng ở khung duyệt, chưa build | Đạt, bằng test tự động |
| E9 | Ghi góp ý, bấm Không đồng ý, làm lại | Hoàn tác, vòng sau hội đồng nhận góp ý, vòng trước không build | Đạt, bằng test tự động |
| E10 | Bấm Không đồng ý, dừng | Kết luận Không được duyệt, code về như cũ, không build | Đạt, bằng test tự động |
| E11 | Để quá 60 phút không duyệt | Tự hoàn tác, kết luận Không được duyệt | Đạt, bằng test tự động |
| E12 | Mở job trên hai tab, duyệt ở tab cũ sau khi đã sang vòng sau | Báo khung duyệt đã sang vòng khác, không duyệt nhầm | Đạt, bằng test tự động |
| E13 | Lỗi đính kèm do planner (giấy vào sai dòng) | Đã sửa trong `pipelines/<thủ tục>/attach/`, tiêu chí `dòng: …` đạt 5/5 | Chưa |

Sau mỗi ca kiểm tra khu làm việc (`~/.autotest-hcc/workspace`): ca không đổi code thì không có file nào bị đổi. Ca Đã sửa thì chỉ có đúng các file trong patch.

## 6. Báo lỗi

Mỗi lỗi ghi: mã kịch bản, mã job (thư mục trong `auto-test-hcc/runs/`), mã req, bước đang ở, tab Nhật ký, ảnh màn hình. Không dán CCCD, họ tên hay ảnh giấy tờ vào hệ thống báo lỗi ngoài công ty. Thư mục `runs/` chứa dữ liệu nhạy cảm, không commit, không gửi đi.

## 7. Giới hạn đã biết

- **Không chạy extension, không mở cổng:** chỉ kiểm được backend. Lỗi engine điền / đính của extension chỉ được báo cáo. Mô phỏng form dựa trên mẫu form đã lưu của thủ tục; thủ tục chưa có mẫu thì tab Mô phỏng form báo chưa có, vẫn xem được Output máy chủ và So sánh các lần.
- **Mốc người nộp:** lượt trợ lý có ngữ cảnh hết hạn thì web hỏi mốc người nộp; thiếu thì vài thủ tục phân vai khác lượt gốc. Web cảnh báo khi chạy lại ra dưới 70% field của lượt gốc.
- **Lỗi đính kèm:** chỉ chấm kế hoạch backend, chưa test lượt đính kèm của Trợ lý hồ sơ, không sinh ca hồi quy.
- **Agent không được sửa** extension, `tests/conftest.py`.
- **Pipeline Bắc Ninh:** vài pipeline dùng lại câu trả lời LLM trong 30 phút, nên các lần chạy không đo được độ dao động của LLM. Web có cảnh báo.

## 8. Chi phí và thời gian

Đo theo giá niêm yết, nếu dùng gói thuê bao thì tính vào hạn mức. Trần mỗi ca là 30 USD.

| Loại ca | Chi phí | Thời gian |
| --- | --- | --- |
| Hội đồng tranh luận nhiều, sửa hai chỗ | khoảng 5,4 USD | khoảng 15 phút |
| Lỗi rõ ràng, sửa trong một vòng | khoảng 2,6 USD | khoảng 10 phút |
| Dừng ở bước trọng tài | khoảng 1,9 USD | khoảng 3 phút |

## 9. Việc tiếp theo

1. Chạy nhóm C với req thật để đối chiếu mô phỏng form với web trace.
2. Chạy E2, E3, E13 với lỗi thật.
3. Thêm mẫu mô phỏng form cho thủ tục chưa có (chép từ Monitor, xem README mục Đồng bộ mô phỏng form).
4. Tự phát hiện lỗi không cần nhập tay.
