# Kế hoạch kiểm thử web Agent tự sửa

Tài liệu cho đội tester, cập nhật ngày 9/11/2026. Đọc xong có thể tự chạy một ca và biết cần kiểm tra gì.

## 1. Web này làm gì

Khi một ô điền sai trên cổng dịch vụ công, người dùng nhập mã req và mô tả lỗi. Hệ thống tự làm phần còn lại:

1. Chạy lại đúng lỗi đó 5 lần trên cổng thật để xem lỗi có lặp lại không.
2. Các agent AI phân tích và tranh luận. Một agent trọng tài quyết định.
3. Lỗi do OCR đọc sai thì báo cáo và bỏ qua, vì OCR sai thì code không thể biết chữ đúng.
4. Lỗi do code thì sửa ở backend (BE) hoặc extension (FE) và chạy test.
5. Test qua thì **dừng chờ người duyệt**: người chạy đọc patch rồi bấm đồng ý thì mới build Docker, nạp extension và chạy lại 5 lần trên cổng.
6. Đạt cả 5 lần thì giữ bản sửa, chưa commit. Không đạt thì tự hoàn tác và họp lại, tối đa 3 vòng.

Trong suốt ca, người chạy làm hai việc: **đăng nhập VNeID** và **duyệt bản sửa** trước khi build.

### Ca thật đầu tiên

Đã chạy trọn một ca trên `dichvucong.gov.vn` với thủ tục Cấp bản sao trích lục hộ tịch:

- Bot vào tới tờ khai 16 giây sau khi nhận đăng nhập, tự chọn cơ quan, tự Xác nhận, form 47 ô.
- Điền 5 lần, mỗi lần 22 thông tin, OCR mới cả 5 lần, ra đủ 19/19 field của lượt gốc.
- Ba thành viên hội đồng ban đầu bất đồng (mapper, LLM, giấy tờ thiếu). Sau phản biện cùng kết luận lỗi ở LLM.
- Hội đồng tìm ra hai lỗi thật: LLM đưa dòng "Nơi chết" vào Nơi cư trú ở cả 5 lần, và ô Cơ quan đăng ký bị cắt mất phần sau ở 3/5 lần.
- Sửa mapper, thêm test, 78 test pipeline pass, toàn bộ test không có đỏ mới, build xong, điền lại trên cổng đạt 5/5, không field nào hồi quy.

## 2. Tài nguyên

### Địa chỉ

| Thành phần | Địa chỉ | Ghi chú |
| --- | --- | --- |
| Web Agent tự sửa | http://localhost:12008 | Giao diện chính |
| Dịch vụ agent | http://127.0.0.1:12009/agent-api/health | Chỉ mở trên máy chạy, trả `{"ok":true,...}` là sống |
| Backend | http://localhost:12005/healthz | Phải trả `{"ok":true,...}` |
| Web Monitor | http://localhost:12007 | Xem trace của một req |
| Cổng thử | https://dichvucong.gov.vn/ | Cổng thật, không có môi trường thử riêng |

### Tài khoản

| Tài khoản | Dùng để | Ghi chú |
| --- | --- | --- |
| Tài khoản super_admin | Đăng nhập web Agent tự sửa | Tài khoản khác bị từ chối |
| Tài khoản test theo đơn vị | Nhập ở ô "Tài khoản chạy lại" | Web tự điền theo req. Quyết định Tỉnh/Xã khi chọn cơ quan |
| VNeID của chính tester | Đăng nhập cổng | Tester tự đăng nhập, bot không biết mật khẩu |

Tài khoản chỉ tồn tại trong Mongo của từng máy, mật khẩu không ghi trong repo. Máy mới tự tạo theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md).

### Dữ liệu thử

Chỉ dùng **req nội bộ**, tức lượt chạy bằng tài khoản test trong Mongo local. Không dùng hồ sơ của người dân thật, vì mỗi lượt agent gửi OCR và ảnh giấy tờ của ca đó lên Anthropic. Lấy mã req ở web Monitor hoặc ô "Mã hỗ trợ" của panel extension.

Mã req không ghi trong tài liệu này vì repo public. Mỗi máy có Mongo riêng, nên phải tự tạo req bằng tài khoản test của máy đó. Thủ tục đã chạy thật là Cấp bản sao trích lục hộ tịch, form SurveyJS trên Cổng DVC quốc gia, nên nên bắt đầu từ thủ tục này.

Một req vừa được sửa xong, chạy lại với cùng lỗi sẽ ra **Không tái hiện**, dùng được cho kịch bản E4.

Req phải là lượt **điền**, không phải lượt đính kèm, và tệp gốc còn trên đĩa. Web báo ngay khi nhập mã nếu không đạt.

### Máy chạy

Cần một máy Windows có repo, Docker Desktop, Python 3.11, Node, Claude Code đã đăng nhập, Playwright và mạng Tailscale tới OCR, LLM. Cài từ đầu theo [HUONG-DAN-F19.md](HUONG-DAN-F19.md). Extension `auto-fill-hcc-extension/api/config.js` phải trỏ `http://localhost:12005`, sai thì web từ chối tạo ca.

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

Tắt dịch vụ agent thì cửa sổ Chromium của bot cũng tắt. Phiên VNeID được giữ trong `auto-test-hcc/.profile/`.

## 3. Cách chạy một ca

1. Mở web, đăng nhập tài khoản super_admin.
2. Nhập mã req. Web hiện tên thủ tục, tài khoản, số tệp.
3. Nhập ô **Lỗi do đâu**: ô nào sai, đúng ra phải thế nào.
4. Nhập mật khẩu tài khoản chạy lại, bấm **Bắt đầu**.
5. Một cửa sổ Chromium mở trang chủ cổng. Bấm **Đăng nhập** và hoàn tất VNeID.
6. Không cần làm gì nữa. Bot tự nhận ra đã đăng nhập, tự vào thủ tục, tự xác nhận, tự điền.
7. Theo dõi trên web. Khi xong, đọc kết luận và patch.

Từ lúc bot tới tờ khai đến lúc kết thúc, **đừng thao tác trên cửa sổ bot**.

Bot kẹt thì web hiện khung vàng ghi rõ cần làm gì. Làm trên cửa sổ bot rồi bấm nút trong khung, bot chạy tiếp.

### Thêm thủ tục mới

Tab **Thêm thủ tục mới** thay cho việc dán đường dẫn file vào Claude trong VS Code.

1. **Link kê khai**: nhập tên, mã, URL trang thủ tục trên cổng. Key tự gợi ý từ tên, sửa cho gọn. Tích các cờ chọn cơ quan, tích Sở,
   chỉ chọn Tỉnh, tự Xác nhận; điều kiện khác ghi vào ô Điều kiện đặc biệt. Thủ tục đã có link thì chọn **Dùng link có sẵn** và gõ key.
2. **Tài liệu**: kéo thả tất cả vào một chỗ. Excel tự vào nhóm mapping, PDF và Word vào file mẫu, ảnh vào ánh xạ đính kèm; xếp sai thì
   đổi nhóm ở từng tệp. Ảnh chụp màn hình dán thẳng bằng Ctrl+V.
3. Ghi yêu cầu thêm nếu có, chọn có đưa lên trợ lý không, nhập tài khoản backend đúng tỉnh của thủ tục, bấm **Bắt đầu làm thủ tục**.

Hệ thống thêm link vào `ke_khai_links.json`, agent làm pipeline điền và đính kèm theo CLAUDE.md, rồi hệ thống chạy test, build Docker
và chạy thử trên file mẫu qua backend. Chưa đạt thì trả lỗi lại cho agent, tối đa 3 lần; vẫn chưa đạt thì hoàn tác sạch, kể cả link.
Đạt thì đọc kỹ khung **Agent tự suy ra, cần kiểm**, rồi bấm **Kiểm thử trên cổng thật** để chạy req vừa chạy thử qua luồng 5 lần ở trên.
Code nằm trong thư mục làm việc, chưa commit; không giữ thì bấm **Hoàn tác thủ tục**.

## 4. Luồng chi tiết

| Bước | Ai làm | Trên web thấy gì |
| --- | --- | --- |
| Thu thập chứng cứ từ req | Hệ thống | Giai đoạn Thu thập |
| Mở trang chủ cổng | Bot | Khung vàng "Đang chờ bạn" |
| Đăng nhập VNeID | **Tester** | Khung vàng tự biến mất khi xong |
| Vào thủ tục qua panel extension, chọn cơ quan theo Tỉnh/Xã, Nộp trực tuyến, Xác nhận | Bot và extension | Giai đoạn Mở cổng |
| Điền 5 lần, mỗi lần tải lại trang | Bot | Giai đoạn Chạy lại, 5 chấm tròn |
| Hội đồng phân tích và phản biện | Agent | Các thẻ ý kiến |
| Trọng tài quyết định | Agent | Thẻ Trọng tài |
| Sửa code | Agent | Thẻ Sửa code, patch |
| Test | Hệ thống | Danh sách kiểm tra |
| Duyệt bản sửa | **Tester** | Khung vàng "Chờ bạn duyệt bản sửa": patch, kết quả test, 3 nút |
| Build Docker, nạp extension | Hệ thống | Dòng Docker trong danh sách kiểm tra |
| Điền lại 5 lần | Bot | Bảng tiêu chí × lần, ảnh cổng |
| Kết luận | Hệ thống | Khung kết luận |

### Các kết luận

| Kết luận | Ý nghĩa | Code có đổi không |
| --- | --- | --- |
| Đã sửa | Đạt cả 5 lần, không field nào đổi ngoài dự kiến | Có, chưa commit |
| Bỏ qua: lỗi OCR | Chữ trên giấy khác chữ OCR đọc ra | Không |
| Chỉ báo cáo | Lỗi do cổng, giấy tờ thiếu, không phải lỗi, hoặc chưa đủ bằng chứng | Không |
| Không tái hiện | Code hiện tại đã đạt 5/5 | Không |
| Cần người xem | Hết số vòng mà chưa đạt | Có: code của vòng trượt gần nhất để lại cho người xem, chưa build lên Docker; không dùng thì bấm Hoàn tác bản sửa. Code người duyệt đã bác hoặc lộ dữ liệu thật thì không để lại |
| Không được duyệt | Người duyệt bấm dừng, hoặc quá 60 phút không ai duyệt | Không, đã tự hoàn tác |

### Duyệt bản sửa

Khi khung vàng **Chờ bạn duyệt bản sửa** hiện, code agent viết đã nằm trong thư mục làm việc và test đã qua, nhưng chưa build Docker và chưa nạp vào extension. Đọc patch rồi chọn:

| Nút | Hệ thống làm gì |
| --- | --- |
| Đồng ý, build và chạy kiểm | Build Docker (nếu đổi BE), nạp extension (nếu đổi FE), chạy lại 5 lần để chấm |
| Không đồng ý, làm lại theo góp ý | Hoàn tác, hội đồng họp lại ở vòng sau và đọc góp ý. Phải ghi góp ý; vòng cuối thì nút này tắt |
| Không đồng ý, dừng | Hoàn tác và kết thúc với kết luận Không được duyệt |

Quá 60 phút không ai bấm thì tự hoàn tác và kết thúc, vì cả hàng đợi đang chờ ca này. Trong lúc chờ có thể sửa tay các file trong patch: hệ thống build đúng nội dung trên đĩa và ghi cảnh báo patch đã đổi.

Đạt hay không do máy chấm trên **giá trị đọc từ form trên cổng**, không phải giá trị backend trả. Backend đúng mà form trống vẫn tính là trượt.

## 5. Kịch bản kiểm thử

Tình trạng ghi ở cột cuối: **Đạt** là đã chạy và đạt, **Chưa** là chưa chạy lần nào. Tester ưu tiên các dòng Chưa.

### A. Web và phân quyền

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| A1 | Đăng nhập tài khoản không phải super_admin | Thấy câu giải thích, không thấy form | Đạt |
| A2 | Mở form, chưa nhập gì | Nút Bắt đầu tắt | Đạt |
| A3 | Nhập mã req không có | Báo không thấy req trong Mongo local | Đạt |
| A4 | Nhập mô tả quá ngắn | Nút Bắt đầu vẫn tắt | Đạt |
| A5 | Sai mật khẩu tài khoản chạy lại | Báo ngay, không tạo ca | Đạt |
| A6 | Tạo ca thứ hai khi ca đầu đang chạy | Ca hai xếp hàng, chạy sau | Đạt |
| A7 | Bấm Dừng khi ca đang chờ đăng nhập | Ca dừng ngay | Đạt |
| A8 | Đóng tab web khi ca đang chạy | Ca vẫn chạy, mở lại xem tiếp được | Đạt |
| A9 | Mở web trên khổ điện thoại | Không tràn ngang | Đạt |
| A10 | Tắt dịch vụ agent rồi mở web | Báo chưa chạy và ghi lệnh bật | Đạt |

### B. Vào cổng thật

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| B1 | Tạo ca | Chromium mở `dichvucong.gov.vn` | Đạt |
| B2 | Đăng nhập VNeID | Trang SSO hiển thị bình thường, không trắng | Đạt |
| B3 | Đăng nhập xong | Khung vàng tự biến mất, không cần bấm | Một phần: mới thấy với phiên còn hạn, cần thử đăng nhập mới trong lúc chờ |
| B4 | Chờ sau đăng nhập | Bot tự vào đúng thủ tục, đúng cơ quan theo Tỉnh/Xã | Đạt |
| B5 | Modal Thông tin chung | Bot tự Xác nhận, vào form | Đạt |
| B6 | Chạy ca thứ hai ngay sau đó | Còn phiên VNeID, không phải đăng nhập lại | Đạt, cả khi tắt mở lại Chromium |
| B7 | Để hết phiên VNeID giữa ca | Web nhắc đăng nhập lại, xong chạy tiếp | Chưa |
| B8 | Đóng cửa sổ Chromium giữa ca | Web nhắc, không chết ca | Đạt |

### C. Vòng điền 5 lần

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| C1 | Tải lại trang sau mỗi lần | Tờ khai về đúng, modal hiện lại thì tự xác nhận | Đạt |
| C2 | Điền 5 lần | 5 mã req khác nhau | Đạt |
| C3 | Đọc form SurveyJS | Giá trị trên bảng khớp với cửa sổ bot | Một phần: số liệu khớp, cần tester so bằng mắt |
| C4 | Xem Chạy lại trên web | "5/5 lần xác nhận OCR mới" | Đạt |
| C5 | Bấm nút Lần 1 ở Ảnh cổng | Hiện ảnh chụp cổng sau khi điền | Đạt |
| C6 | Mở tab Kết quả điền | Có 2 đợt Trước khi sửa và Sau sửa, so được từng lần | Đạt |

### D. Chặn nộp hồ sơ

Quan trọng nhất. Bot phải không bao giờ nộp hồ sơ.

| Mã | Thao tác | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| D1 | Khi bot đang điền, tự bấm "Lưu và nộp hồ sơ" trên cửa sổ bot | Nút không có tác dụng, nhật ký ghi đã chặn | Chưa |
| D2 | Sau ca, tra hồ sơ của tài khoản VNeID trên cổng | Không có hồ sơ nào được nộp | Chưa |
| D3 | Cùng lúc đó, xem cổng có tạo hồ sơ nháp không | Ghi lại để biết cổng có lưu nháp dữ liệu không | Chưa |

Lớp chặn đã kiểm bằng cú click thật trong trình duyệt tự động. Trong ca thật, qua 10 lần điền không có request nộp nào đi ra; lớp chặn chỉ huỷ nhầm request đọc phí `get-formality-case-fees`, đã sửa để lệnh đọc được đi qua. Chưa ai thử bấm nút nộp trên cổng thật. Khi làm D1, **dừng lại nếu nút có vẻ hoạt động**, báo ngay, đừng bấm tiếp ở bước xác nhận.

Nhật ký job có dòng "Request ghi lên cổng trong đợt này", liệt kê đường dẫn cổng đã nhận. Dòng này giúp trả lời D3 và cần gửi lại cho người phụ trách để siết lớp chặn.

### E. Phân tích và sửa lỗi

| Mã | Tình huống | Kết quả mong đợi | Tình trạng |
| --- | --- | --- | --- |
| E1 | Lỗi ở BE | Đã sửa, test BE và build chạy, tiêu chí trượt trước sửa thành 5/5 sau sửa | Đạt trên cổng thật, với lỗi thật |
| E2 | Lỗi engine điền ở FE | Đã sửa, test extension chạy, extension nạp lại, không build Docker | Chưa |
| E3 | Lỗi OCR thật | Bỏ qua, nêu trên giấy ghi gì và OCR ra gì, không đổi code | Chưa |
| E4 | Mô tả một lỗi không có thật | Không tái hiện hoặc Chỉ báo cáo, không đổi code | Chưa |
| E5 | Bản sửa trượt | Tự hoàn tác, họp lại với lý do thất bại | Đạt, bằng test tự động |
| E5b | Trượt hết số vòng (Cần người xem) | Code của vòng cuối còn trong thư mục làm việc, có cảnh báo "CHƯA ĐẠT", Docker vẫn chạy code gốc, bấm Hoàn tác bản sửa thì về như cũ | Đạt, bằng test tự động |
| E6 | Bấm Hoàn tác bản sửa sau khi xong | File về như cũ, build lại nếu đổi BE | Đạt, bằng test tự động |
| E7 | Bấm Dừng khi agent đang sửa | Code về như cũ | Đạt, bằng test tự động |
| E8 | Bản sửa qua test | Dừng ở khung duyệt, chưa build Docker, chưa nạp extension | Đạt, bằng test tự động |
| E9 | Ghi góp ý, bấm Không đồng ý, làm lại | Hoàn tác, vòng sau hội đồng nhận góp ý, vòng trước không build | Đạt, bằng test tự động |
| E10 | Bấm Không đồng ý, dừng | Kết luận Không được duyệt, code về như cũ, không build | Đạt, bằng test tự động |
| E11 | Để quá 60 phút không duyệt | Tự hoàn tác, kết luận Không được duyệt | Đạt, bằng test tự động |
| E12 | Mở job trên hai tab, duyệt ở tab cũ sau khi đã sang vòng sau | Báo khung duyệt đã sang vòng khác, không duyệt nhầm | Đạt, bằng test tự động |

Sau mỗi ca kiểm tra `git status`: ca không đổi code thì không có file nào trong `auto-fill-hcc-backend/` hay `auto-fill-hcc-extension/` bị đổi. Ca Đã sửa thì chỉ có đúng các file trong patch.

### F. Thêm thủ tục mới

| Mã | Làm gì | Mong đợi | Trạng thái |
| --- | --- | --- | --- |
| F1 | Kéo thả Excel, ảnh, PDF cùng lúc vào vùng chung | Tự xếp đúng 3 nhóm, đổi nhóm được | Chưa |
| F2 | Dán ảnh chụp màn hình bằng Ctrl+V | Ảnh vào nhóm ánh xạ đính kèm | Chưa |
| F3 | Thả tệp .xls, .exe, tệp quá 40 MB | Báo lý do, không nhận | Chưa |
| F4 | Key trùng link đã có / mã trùng thủ tục khác | Báo trùng, gợi ý dùng link có sẵn / cảnh báo mã | Chưa |
| F5 | Làm một thủ tục thật có đủ mapping, ảnh, file mẫu | Đã làm xong, chạy thử ra ô có giá trị, có req | Chưa |
| F6 | Bấm Dừng khi agent đang viết | Code và link kê khai về như cũ, không còn thư mục pipeline rỗng | Đạt, bằng test tự động |
| F7 | Agent không đạt sau 3 lần | Hoàn tác sạch, build lại backend | Đạt, bằng test tự động |
| F8 | Bấm Hoàn tác thủ tục sau khi xong | Gỡ link, xoá file tạo mới, build lại | Đạt, bằng test tự động |
| F9 | Từ job xong bấm Kiểm thử trên cổng thật | Mở tab sửa lỗi, điền sẵn req chạy thử | Chưa |

## 6. Báo lỗi

Mỗi lỗi ghi: mã kịch bản, mã job (thư mục trong `auto-test-hcc/runs/`), mã req, bước đang ở, tab Nhật ký, ảnh màn hình. Không dán CCCD, họ tên hay ảnh giấy tờ vào hệ thống báo lỗi ngoài công ty. Thư mục `runs/` và `.profile/` chứa dữ liệu nhạy cảm, không commit, không gửi đi.

## 7. Giới hạn đã biết

- **Mốc người nộp:** trên cổng, người nộp là tài khoản VNeID của tester, không phải người trong hồ sơ. Thủ tục phân vai theo mốc này có thể điền khác lượt gốc. Web cảnh báo khi chạy lại ra dưới 70% field của lượt gốc.
- **Chỉ lỗi điền:** chưa xử lý lỗi đính kèm.
- **Chỉ req nội bộ:** không đọc được req trên server.
- **Vào thủ tục tự động** chỉ áp dụng cho thủ tục có trong danh sách "Mở trang thủ tục" của panel. Thủ tục khác bot sẽ nhờ tester mở tay.
- **Bước Thông tin chủ hồ sơ** của wizard cũ, nếu gặp, bot dừng và nhờ tester bấm qua.
- **Agent không được sửa** `api/config.js`, `manifest.json`, bộ đọc form `form-snapshot` và `tests/conftest.py`.
- **Chế độ Chỉ gọi backend** vẫn có trên form, nhanh và không cần VNeID, nhưng không biết form nhận được gì và không sửa được extension.
- **Pipeline Bắc Ninh:** vài pipeline dùng lại câu trả lời LLM trong 30 phút, nên các lần chạy không đo được độ dao động của LLM. Web có cảnh báo.

## 8. Chi phí và thời gian

Đo theo giá niêm yết, nếu dùng gói thuê bao thì tính vào hạn mức. Trần mỗi ca là 30 USD.

| Loại ca | Chi phí | Thời gian |
| --- | --- | --- |
| Lỗi thật trên cổng, hội đồng tranh luận nhiều, sửa hai chỗ | 5,40 USD | 17 phút |
| Lỗi rõ ràng, sửa trong một vòng | khoảng 2,6 USD | khoảng 10 phút |
| Dừng ở bước trọng tài | khoảng 1,9 USD | khoảng 3 phút |
| Thêm thủ tục mới | chưa đo; trần 25 USD mỗi lượt agent, 60 USD cả job | agent tối đa 60 phút mỗi lượt |

## 9. Việc tiếp theo

1. Làm nhóm D và các dòng còn lại của nhóm B, C. Nhóm D là điều kiện để dùng chính thức.
2. Chạy E2 và E3 với lỗi thật.
3. Thử thêm các loại form khác trên cổng và ghi mẫu req vào mục Dữ liệu thử. Mới chạy thật một thủ tục.
4. Siết lớp chặn mạng theo đúng request nộp của cổng, và xử lý mốc người nộp nếu nó làm sai kết quả.
5. Mở rộng sang lỗi đính kèm và tự phát hiện lỗi không cần nhập tay.
