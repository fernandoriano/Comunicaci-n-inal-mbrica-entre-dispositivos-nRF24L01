#Tx mejorado - ORIGINAL EXACTO + OLED FIJA
from machine import Pin, SPI, ADC, I2C
import utime, struct
from nrf24l01 import NRF24L01
from ssd1306 import SSD1306_I2C

# ---- OLED (I2C1: GP11 SCL, GP10 SDA) ----
i2c = I2C(1, scl=Pin(11), sda=Pin(10), freq=400000)
oled = SSD1306_I2C(128, 64, i2c, addr=0x3C)
oled.fill(0)
oled.text("TX: NRF24L01", 0, 0)
oled.text("Vel: 2Mbps", 0, 16)
oled.text("Canal: 100", 0, 32)
oled.text("Ang: 0-180", 0, 48)
oled.show()

# ---- Radio SPI0 ----
spi = SPI(0, sck=Pin(6), mosi=Pin(7), miso=Pin(4))
csn = Pin(15, Pin.OUT, value=1)
ce  = Pin(14, Pin.OUT, value=0)

nrf = NRF24L01(spi, csn, ce, payload_size=4)

TX_ADDR = b'\xE1\xF0\xF0\xF0\xF0'
RX_ADDR = b'\xD2\xF0\xF0\xF0\xF0'

nrf.open_tx_pipe(TX_ADDR)
nrf.open_rx_pipe(1, RX_ADDR)

# Configuración MÁXIMA velocidad
nrf.set_power_speed(0, 2)  # 0dBm, 2Mbps (MÁXIMA VELOCIDAD)
nrf.reg_write(0x01, 0x00)  # No Auto-Ack
nrf.reg_write(0x04, 0x00)  # No retransmisiones
nrf.reg_write(0x05, 100)   # Canal 100 (menos interferencia)
nrf.stop_listening()

# ---- Joystick con mapeo directo 0-180° ----
adc_x = ADC(Pin(26))

def leer_angulo_joystick():
    raw = adc_x.read_u16()  # 0-65535
    # Mapeo directo: 0=0°, 32767=90°, 65535=180°
    angulo = int((raw * 180) / 65535)
    return max(0, min(180, angulo))

def calcular_checksum(sync, angulo):
    return (sync + (angulo & 0xFF) + ((angulo >> 8) & 0xFF)) & 0xFF

SYNC_BYTE = 0xA5
angulo_anterior = -1
umbral = 0  # Enviar TODOS los cambios (máxima respuesta)

print("🎮 TX Joystick - Rango 0-180° - 2Mbps - Listo")

while True:
    angulo_actual = leer_angulo_joystick()
    
    # Enviar SIEMPRE (umbral = 0 para máxima respuesta)
    checksum = calcular_checksum(SYNC_BYTE, angulo_actual)
    paquete = struct.pack("<BHB", SYNC_BYTE, angulo_actual, checksum)
    
    try:
        nrf.send(paquete)
        if angulo_actual != angulo_anterior:
            print(f"📤 TX: {angulo_actual}°")
            angulo_anterior = angulo_actual
    except Exception as e:
        print(f"❌ Error: {e}")
        nrf.reg_write(0x07, 0x70)
    
    utime.sleep_ms(10)  # ⚡ SOLO 10ms = 100 FPS!