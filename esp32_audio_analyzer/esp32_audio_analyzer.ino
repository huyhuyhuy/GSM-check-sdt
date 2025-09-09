#include <driver/adc.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>

// Pin definitions for 2 multiplexers
#define MUX_S0 25
#define MUX_S1 26
#define MUX_S2 27
#define MUX_S3 14
#define MUX1_EN 32  // Enable cho MUX #1 (SIM 1-16)
#define MUX2_EN 33  // Enable cho MUX #2 (SIM 17-32)
#define ADC_PIN 36  // VP pin

// Channel mapping
#define CHANNELS_PER_MUX 16
#define TOTAL_CHANNELS 32

// CHIẾN LƯỢC TỐI ƯU RAM:
// 1. Chỉ 1 channel active tại một thời điểm
// 2. Giảm buffer size
// 3. Sử dụng uint16_t thay vì int
// 4. Loại bỏ debug variables không cần thiết

// === Streaming (PC-side old method) ===
volatile bool stream_active = false;      // Đang streaming liên tục
volatile bool binary_mode = true;         // Gửi dạng binary 3 bytes: [ch][hi][lo]
int stream_channels[2] = {1, 2};          // Mặc định chỉ 2 kênh: 1 và 2 (0-31)
int stream_channel_count = 2;             // Chỉ stream 2 kênh
TaskHandle_t streamTaskHandle = NULL;     // Task handle cho streaming

// Real-time detection - không cần buffer
// Memory usage: ~50 bytes thay vì 2KB

// Multiplexer selection optimized for 2 fixed channels on MUX #1
void selectChannel(int channel) {
    if (channel < 0 || channel >= TOTAL_CHANNELS) return;
    // Chỉ dùng MUX #1 (SIM 1-16). Không bật/tắt EN mỗi lần nữa
    int mux_channel = channel % CHANNELS_PER_MUX;
    digitalWrite(MUX_S0, mux_channel & 0x01);
    digitalWrite(MUX_S1, (mux_channel >> 1) & 0x01);
    digitalWrite(MUX_S2, (mux_channel >> 2) & 0x01);
    digitalWrite(MUX_S3, (mux_channel >> 3) & 0x01);
    delay(2); // Small delay for MUX switching
}

// Initialize ADC
void setupADC() {
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_0, ADC_ATTEN_DB_11);
}

// Read audio sample
uint16_t readAudioSample() {
    return (uint16_t)adc1_get_raw(ADC1_CHANNEL_0);
}

// Gửi một mẫu ADC của kênh chỉ định theo định dạng hiện tại
inline void sendSample(int channel, uint16_t value) {
    if (binary_mode) {
        // 3 bytes: [channel][value_high][value_low]
        uint8_t buf[3];
        buf[0] = (uint8_t)channel;
        buf[1] = (uint8_t)((value >> 8) & 0xFF);
        buf[2] = (uint8_t)(value & 0xFF);
        Serial.write(buf, 3);
    } else {
        // Text mode: "CH<channel>: <value>\n"
        Serial.print("CH");
        Serial.print(channel);
        Serial.print(": ");
        Serial.println(value);
    }
}

// Task stream liên tục 2 kênh (mặc định 1 và 2) với batching và warm-up
void streamTask(void *parameter) {
    const uint32_t yield_interval_us = 5000; // nhường CPU mỗi 5ms
    const int WARMUP_READS = 2;              // đọc bỏ để ổn định sau switch
    const int BLOCK_SIZE = 12;               // số mẫu gửi liên tiếp cho mỗi kênh
    uint8_t tx[BLOCK_SIZE * 3];              // buffer gửi 3 bytes/mẫu
    uint32_t last_yield_micros = 0;

    while (true) {
        if (stream_active) {
            for (int i = 0; i < stream_channel_count; ++i) {
                int ch = stream_channels[i];
                if (ch < 0 || ch >= TOTAL_CHANNELS) {
                    continue;
                }
                selectChannel(ch);
                delayMicroseconds(400);
                // Warm-up discard
                for (int w = 0; w < WARMUP_READS; ++w) {
                    (void)readAudioSample();
                }
                // Thu BLOCK_SIZE mẫu và đóng gói
                int idx = 0;
                for (int b = 0; b < BLOCK_SIZE; ++b) {
                    uint16_t v = readAudioSample();
                    tx[idx++] = (uint8_t)ch;
                    tx[idx++] = (uint8_t)((v >> 8) & 0xFF);
                    tx[idx++] = (uint8_t)(v & 0xFF);
                }
                // Chờ UART sẵn sàng
                while (Serial.availableForWrite() < (int)sizeof(tx)) {
                    delayMicroseconds(200);
                    taskYIELD();
                }
                Serial.write(tx, sizeof(tx));
            }

            uint32_t now = micros();
            if (now - last_yield_micros >= yield_interval_us) {
                last_yield_micros = now;
                vTaskDelay(1); // ~1ms
            }
        } else {
            vTaskDelay(1);
        }
    }
}

void setup() {
    Serial.begin(250000);
    
    // Initialize multiplexer pins
    pinMode(MUX_S0, OUTPUT);
    pinMode(MUX_S1, OUTPUT);
    pinMode(MUX_S2, OUTPUT);
    pinMode(MUX_S3, OUTPUT);
    pinMode(MUX1_EN, OUTPUT);
    pinMode(MUX2_EN, OUTPUT);
    
    // Bật cố định MUX #1, tắt MUX #2 cho phiên 2 kênh
    digitalWrite(MUX1_EN, LOW);
    digitalWrite(MUX2_EN, HIGH);
    
    // Initialize ADC
    setupADC();
    
    // Tạo streaming task
    xTaskCreatePinnedToCore(
        streamTask,
        "StreamTask",
        6144,
        NULL,
        1,
        &streamTaskHandle,
        0
    );

    Serial.println("ESP32 Audio Streamer Ready (2-channel)");
    Serial.println("Commands: start_multi <c1,c2> | start_stream <c> | stop_stream | binary_on | binary_off | status");
}

void loop() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        Serial.print("Received command: ");
        Serial.println(command);
        
        if (command == "binary_on") {
            binary_mode = true;
            Serial.println("BINARY_MODE_ON");
        }
        else if (command == "binary_off") {
            binary_mode = false;
            Serial.println("TEXT_MODE_ON");
        }
        else if (command.startsWith("start_multi ")) {
            // Ví dụ: start_multi 1,2  (chỉ xử lý tối đa 2 kênh)
            String list_str = command.substring(12);
            list_str.trim();

            // Tách danh sách
            int commaIndex = list_str.indexOf(',');
            int c1 = -1, c2 = -1;
            if (commaIndex >= 0) {
                String s1 = list_str.substring(0, commaIndex);
                String s2 = list_str.substring(commaIndex + 1);
                c1 = s1.toInt();
                c2 = s2.toInt();
            } else {
                c1 = list_str.toInt();
            }

            // Validate và áp dụng mặc định nếu cần
            int temp_channels[2] = {1, 2};
            int count = 0;
            if (c1 >= 0 && c1 < TOTAL_CHANNELS) {
                temp_channels[count++] = c1;
            }
            if (c2 >= 0 && c2 < TOTAL_CHANNELS) {
                if (count < 2) temp_channels[count++] = c2;
            }
            if (count == 0) {
                // fallback mặc định kênh 1 và 2
                stream_channels[0] = 1;
                stream_channels[1] = 2;
                stream_channel_count = 2;
            } else if (count == 1) {
                stream_channels[0] = temp_channels[0];
                stream_channel_count = 1;
            } else {
                stream_channels[0] = temp_channels[0];
                stream_channels[1] = temp_channels[1];
                stream_channel_count = 2;
            }

            // Bắt đầu streaming
            stream_active = true;
            Serial.print("MULTI_STREAM_START:");
            Serial.println(stream_channel_count);
        }
        else if (command.startsWith("start_stream ")) {
            // Ví dụ: start_stream 1 (một kênh)
            String ch_str = command.substring(13);
            int ch = ch_str.toInt();
            if (ch >= 0 && ch < TOTAL_CHANNELS) {
                stream_channels[0] = ch;
                stream_channel_count = 1;
            } else {
                stream_channels[0] = 1; // mặc định
                stream_channel_count = 1;
            }
            stream_active = true;
            Serial.println("STREAM_START");
        }
        else if (command == "stop_stream") {
            stream_active = false;
            Serial.println("STREAM_STOP");
        }
        else if (command == "status") {
            Serial.print("Streaming: ");
            Serial.println(stream_active ? "YES" : "NO");
            Serial.print("Binary mode: ");
            Serial.println(binary_mode ? "ON" : "OFF");
            Serial.print("Stream channels: ");
            for (int i = 0; i < stream_channel_count; ++i) {
                Serial.print(stream_channels[i]);
                if (i + 1 < stream_channel_count) Serial.print(",");
            }
            Serial.println();
            Serial.print("Free heap: ");
            Serial.println(ESP.getFreeHeap());
        }
    }
}