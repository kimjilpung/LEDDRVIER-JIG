import pyvisa

def list_and_check_instruments():
    """
    1) PC에 연결된 VISA 계측기 목록을 검색하고
    2) 각 계측기에 실제로 연결해서 *IDN? 명령을 보내
       통신이 정상인지 확인하는 함수.
    """
    try:
        # 1. VISA 리소스 매니저 생성 (NI-VISA를 내부적으로 사용)
        rm = pyvisa.ResourceManager()  # 필요 시 ResourceManager("@ni") 사용 가능
    except Exception as e:
        print("[오류] VISA 리소스 매니저를 생성하지 못했습니다.")
        print(" - NI-VISA가 설치되어 있는지 확인해 주세요.")
        print(" - 관리자 권한 문제일 수도 있습니다.")
        print("예외 메시지:", e)
        return

    try:
        # 2. 현재 연결된 모든 리소스(계측기) 목록 가져오기
        resources = rm.list_resources()

        if not resources:
            print("현재 PC에서 감지된 계측기가 없습니다.")
            print(" - NI MAX에서 장비가 보이는지 먼저 확인해 보세요.")
            return

        print("=== VISA 리소스 목록 ===")
        for i, res in enumerate(resources, start=1):
            print(f"{i}. {res}")
        print("========================\n")

        # GPIB 장비만 따로 필터링 (원하면 전체 리소스 대상으로도 체크 가능)
        gpib_resources = [r for r in resources if r.upper().startswith("GPIB")]

        if not gpib_resources:
            print("VISA에서 GPIB 장비는 감지되지 않았습니다.")
            print(" - GPIB 케이블 연결 및 계측기 전원 상태를 확인해 주세요.")
            return

        print("GPIB 장비 통신 확인 시작...\n")

        # 3. 각 GPIB 계측기에 실제로 접속해서 *IDN? 질의
        for addr in gpib_resources:
            print(f"--- [{addr}] ---")
            try:
                # 계측기 열기
                inst = rm.open_resource(addr)

                # 타임아웃 (ms 단위) 설정 – 너무 짧으면 타임아웃 오류 자주 발생
                inst.timeout = 5000  # 5초

                # 버퍼/상태 초기화 (필요 시)
                try:
                    inst.clear()
                except Exception:
                    # 일부 장비는 clear를 지원하지 않을 수 있음 → 무시
                    pass

                # *IDN? 명령 보내고 응답 받기
                try:
                    response = inst.query("*IDN?")
                    print("연결 성공! 계측기 응답:")
                    print(" ", response.strip())
                except pyvisa.errors.VisaIOError as e:
                    print("장비에 연결은 되었지만 *IDN? 명령에 대한 응답이 없습니다.")
                    print(" - 이 장비가 SCPI를 지원하지 않거나, *IDN? 명령을 지원하지 않을 수 있습니다.")
                    print("VISA IO Error:", e)
                finally:
                    # 리소스(계측기) 닫기
                    inst.close()

            except pyvisa.errors.VisaIOError as e:
                print("이 GPIB 주소로는 계측기를 열 수 없습니다.")
                print(" - GPIB Address가 올바른지, 전원이 켜져 있는지 확인해 주세요.")
                print("VISA IO Error:", e)
            except Exception as e:
                print("예상치 못한 오류가 발생했습니다.")
                print("예외 메시지:", e)

            print()  # 장비 간 구분용 빈 줄

    finally:
        # 리소스 매니저 닫기 (선택사항, 프로그램 종료 시 자동 정리되기도 함)
        try:
            rm.close()
        except Exception:
            pass


if __name__ == "__main__":
    """
    이 스크립트를 직접 실행했을 때 동작.
    (다른 코드에서 import 해서 함수만 호출할 수도 있음)
    """
    list_and_check_instruments()
