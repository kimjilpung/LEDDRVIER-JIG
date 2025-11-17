# Optimized LED Driver Tester - CustomTkinter Version
import customtkinter as ctk
import tkinter.messagebox as msgbox
import pyvisa
import re

class InstrumentController:
    def __init__(self):
        self.rm = pyvisa.ResourceManager()
        self.psu_12v = None
        self.dmm = None
        self.psu_dimming = None
        self.scope = None
        self.offset_current = 0

    def initialize_instruments(self):
        try:
            # Open resources
            self.psu_12v = self.rm.open_resource("GPIB0::5::INSTR")
            self.dmm = self.rm.open_resource("GPIB0::22::INSTR")
            self.psu_dimming = self.rm.open_resource("GPIB0::6::INSTR")
            self.scope = self.rm.open_resource("GPIB0::18::INSTR")

            # Reset and configure
            self.psu_12v.write("*RST; *CLS; CURR 7.5")
            self.psu_dimming.write("*RST; *CLS; INST:NSEL 1; VOLT 5; CURR 1; OUTP OFF")
            self.dmm.write("ZERO:AUTO ON; CONF:CURR:DC 0.1")
            # Use OPC? instead of sleep
            self.dmm.query("*OPC?")
            self.offset_current = float(self.dmm.query("READ?"))
            return "장비 초기화 완료"
        except Exception as e:
            return f"초기화 실패: {e}"

    def measure_all(self, input_v, target_v, target_i_max, target_i_min, target_freq):
        try:
            # Apply input voltage
            self.psu_12v.write(f"VOLT {input_v}; OUTP ON")
            self.psu_12v.query("*OPC?")
            # Ensure dimming off
            self.psu_dimming.write("OUTP OFF")

            # Measure voltage
            self.dmm.write("*RST; CONF:VOLT:DC 100")
            self.dmm.query("*OPC?")
            voltage = float(self.dmm.query("READ?"))

            # Measure MAX current
            self.dmm.write("*RST; CONF:CURR:DC 0.1")
            self.dmm.query("*OPC?")
            current_max = float(self.dmm.query("READ?")) - self.offset_current

            # Measure frequency
            self.scope.write("MEASU:IMM:TYPE FREQuency; MEASU:IMM:SOUR CH1")
            self.scope.query("*OPC?")
            resp = self.scope.query("MEASU:IMM:VAL?").strip()
            match = re.search(r"([-+]?[0-9]*\\.?[0-9]+(?:E[+-]?[0-9]+)?)", resp)
            freq = float(match.group()) / 1000 if match else 0

            # Apply dimming and measure MIN current
            self.psu_dimming.write("OUTP ON")
            self.psu_dimming.query("*OPC?")
            self.dmm.write("*RST; CONF:CURR:DC 0.1")
            self.dmm.query("*OPC?")
            current_min = float(self.dmm.query("READ?")) - self.offset_current
            dim_voltage = float(self.psu_dimming.query("MEAS:VOLT?"))

            # Turn off outputs
            self.psu_12v.write("OUTP OFF")
            self.psu_dimming.write("OUTP OFF")

            return {
                "전압": voltage,
                "전류_MAX": current_max * 1000,
                "전류_MIN": current_min * 1000,
                "DIM 전압": dim_voltage,
                "주파수": freq
            }
        except Exception as e:
            raise RuntimeError(f"측정 오류: {e}")

class TestApp(ctk.CTk):
    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("LED DRIVER TESTER")
        self.geometry("700x800")

        self.iv = ctk.IntVar(value=12)
        self.create_widgets()

    def create_widgets(self):
        ctk.CTkLabel(self, text="LED DRIVER TESTER", font=("Arial", 28, "bold")).pack(pady=10)
        ctk.CTkLabel(self, text="Powered by GCCT", font=("Arial", 14)).pack(pady=3)

        frame = ctk.CTkFrame(self)
        frame.pack(pady=5)
        ctk.CTkLabel(frame, text="입력 전압").grid(row=0, column=0, padx=5)
        ctk.CTkRadioButton(frame, text="12V", variable=self.iv, value=12).grid(row=0, column=1)
        ctk.CTkRadioButton(frame, text="24V", variable=self.iv, value=24).grid(row=0, column=2)

        self.v_entry = self.make_entry("출력 전압(V)")
        self.imax_entry = self.make_entry("전류 MAX 기준(mA)")
        self.imin_entry = self.make_entry("전류 MIN 기준(mA)")
        self.freq_entry = self.make_entry("주파수 기준(kHz)")

        ctk.CTkButton(self, text="장비 초기화", command=self.on_init).pack(pady=10)
        ctk.CTkButton(self, text="측정 시작", command=self.on_measure).pack(pady=10)

        self.result_label = ctk.CTkLabel(self, text="결과 대기 중...", font=("Arial", 20))
        self.result_label.pack(pady=10)

        self.textbox = ctk.CTkTextbox(self, width=600, height=300, font=("Consolas", 14))
        self.textbox.pack(pady=10)

    def make_entry(self, label):
        ctk.CTkLabel(self, text=label).pack()
        entry = ctk.CTkEntry(self)
        entry.pack(pady=5)
        return entry

    def on_init(self):
        msg = self.controller.initialize_instruments()
        self.textbox.delete("0.0", ctk.END)
        self.textbox.insert(ctk.END, msg + "\n")
        self.result_label.configure(text=msg, text_color="green" if "완료" in msg else "red")

    def on_measure(self):
        try:
            iv = self.iv.get()
            v = float(self.v_entry.get())
            imax = float(self.imax_entry.get())
            imin = float(self.imin_entry.get())
            freq = float(self.freq_entry.get())

            result = self.controller.measure_all(iv, v, imax, imin, freq)
            self.textbox.delete("0.0", ctk.END)

            summary = ""
            pass_flag = True
            for key, val in result.items():
                if key == "전압": ref, tol, unit = v, v * 0.10, "V"
                elif key == "전류_MAX": ref, tol, unit = imax, imax * 0.10, "mA"
                elif key == "전류_MIN": ref, tol, unit = imin, imin * 0.10, "mA"
                elif key == "DIM 전압": ref, tol, unit = 5.0, 0.3, "V"
                elif key == "주파수": ref, tol, unit = freq, 30, "kHz"
                status = "PASS" if abs(val - ref) <= tol else "FAIL"
                summary += f"{key}: {val:.2f} {unit} ({status})\n"
                if status == "FAIL": pass_flag = False

            self.textbox.insert(ctk.END, summary)
            self.result_label.configure(text="✅ PASS" if pass_flag else "❌ FAIL", text_color="cyan" if pass_flag else "red")

        except Exception as e:
            msgbox.showerror("오류", str(e))
            self.result_label.configure(text="❌ 오류", text_color="red")

if __name__ == "__main__":
    controller = InstrumentController()
    app = TestApp(controller)
    app.mainloop()
