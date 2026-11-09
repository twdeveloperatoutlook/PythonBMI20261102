import re
import unittest

from app import app, bmi_guidance


class BmiAppTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_initial_page(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        page = response.get_data(as_text=True)
        self.assertIn("了解自己的<br><em>健康狀況。</em>", page)
        self.assertIn("計算你的 BMI", page)
        self.assertNotIn('class="bmi-gauge"', page)

    def test_calculation_and_advice(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("22.5", page)
        self.assertIn("健康體位", page)
        self.assertIn("維持均衡飲食", page)
        self.assertIn('transform="rotate(11.25 180 180)"', page)
        self.assertIn("目前 BMI 22.5，健康體位", page)
        for band in ["low", "healthy", "high", "obese"]:
            self.assertIn(f'class="gauge-{band}"', page)

    def test_gauge_positions_and_categories(self):
        for bmi, angle, category in [
            ("0.1", -89.55, "體重過輕"),
            ("18.4", -7.2, "體重過輕"),
            ("18.5", -6.75, "健康體位"),
            ("23.9", 17.55, "健康體位"),
            ("24", 18.0, "體重過重"),
            ("26.9", 31.05, "體重過重"),
            ("27", 31.5, "肥胖"),
            ("40", 90.0, "肥胖"),
            ("50", 90.0, "肥胖"),
            ("1e308", 90.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                response = self.client.post("/", data={"height": "100", "weight": bmi})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn(f"目前 BMI {float(bmi):.1f}，{category}", page)
                needle = re.search(r'transform="rotate\(([-\d.]+) 180 180\)"', page)
                self.assertIsNotNone(needle)
                self.assertAlmostEqual(float(needle.group(1)), angle)
                self.assertEqual('class="gauge-note"' in page, float(bmi) > 40)

    def test_gauge_uses_displayed_bmi_at_threshold(self):
        page = self.client.post(
            "/", data={"height": "100", "weight": "23.96"}
        ).get_data(as_text=True)
        self.assertIn("目前 BMI 24.0，體重過重", page)
        self.assertIn('transform="rotate(18.0 180 180)"', page)

    def test_taiwan_adult_thresholds(self):
        for bmi, category in [
            (18.4, "體重過輕"),
            (18.5, "健康體位"),
            (23.9, "健康體位"),
            (24.0, "體重過重"),
            (26.9, "體重過重"),
            (27.0, "肥胖"),
        ]:
            with self.subTest(bmi=bmi):
                self.assertEqual(bmi_guidance(bmi)["label"], category)

    def test_invalid_fields_do_not_produce_result(self):
        for height, weight in [("", "65"), ("0", "65"), ("abc", "65"), ("170", "-2"), ("inf", "65"), ("170", "nan"), ("1e-300", "65"), ("1e308", "65"), ("1", "1e308")]:
            with self.subTest(height=height, weight=weight):
                response = self.client.post("/", data={"height": height, "weight": weight})
                page = response.get_data(as_text=True)
                self.assertEqual(response.status_code, 200)
                self.assertIn('aria-invalid="true"', page)
                self.assertNotIn("YOUR RESULT", page)
                self.assertNotIn('class="bmi-gauge"', page)

    def test_name_is_included_in_advice(self):
        response = self.client.post(
            "/", data={"name": "小美", "height": "170", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertIn("給 小美 的健康建議", page)
        self.assertIn("小美，你的體位屬於", page)
        self.assertIn("小美，維持均衡飲食", page)
        self.assertIn('value="小美"', page)

    def test_name_is_optional(self):
        response = self.client.post("/", data={"height": "170", "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertIn("給你的健康建議", page)
        self.assertIn("你的體位屬於", page)

    def test_name_is_escaped(self):
        response = self.client.post(
            "/", data={"name": "<script>alert(1)</script>", "height": "170", "weight": "65"}
        )
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)

    def test_input_is_escaped(self):
        response = self.client.post("/", data={"height": '<script>alert(1)</script>', "weight": "65"})
        page = response.get_data(as_text=True)
        self.assertNotIn("<script>", page)
        self.assertIn("請輸入大於 0", page)


if __name__ == "__main__":
    unittest.main()
