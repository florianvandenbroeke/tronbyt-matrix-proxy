#include <WiFi.h>
#include <ESP32-HUB75-MatrixPanel-I2S-DMA.h>
#include <HTTPClient.h>
#include <WiFiClientSecure.h>

/************ HUB75 PINOUT ************/
#define R1 2
#define G1 4
#define BL1 15
#define R2 16
#define G2 17
#define BL2 27
#define CH_A 5
#define CH_B 18
#define CH_C 19
#define CH_D 21
#define CH_E 12
#define CLK 22
#define LAT 26
#define OE 25

const char* ssid     = "It hurts when IP";
const char* password = "Pannekoek";

/************ PROXY URL ************/
const char* imageUrl = "https://tronbyt-matrix-proxy.onrender.com/matrix";

static uint8_t imageBuffer[64 * 32 * 2];     // actief frame
static uint8_t downloadBuffer[64 * 32 * 2];  // tijdelijke buffer

#define PANEL_RES_X 64      // Number of pixels wide of each INDIVIDUAL panel module. 
#define PANEL_RES_Y 64     // Number of pixels tall of each INDIVIDUAL panel module.
#define PANEL_CHAIN 1      // Total number of panels chained one to another
 
//MatrixPanel_I2S_DMA dma_display;
MatrixPanel_I2S_DMA *dma_display = nullptr;

bool downloadImageRobust() {
  WiFiClientSecure client;
  client.setInsecure();

  HTTPClient https;
  if (!https.begin(client, imageUrl)) return false;

  int httpCode = https.GET();
  if (httpCode != HTTP_CODE_OK) {
    https.end();
    return false;
  }

  WiFiClient* stream = https.getStreamPtr();
  size_t index = 0;
  unsigned long start = millis();

  while (index < sizeof(downloadBuffer) && millis() - start < 3000) {
    if (stream->available()) {
      downloadBuffer[index++] = stream->read();
    }
  }

  https.end();

  // accepteer frame als ≥ 95% binnen is
  if (index < sizeof(downloadBuffer) * 0.95) {
    Serial.printf("Partial frame rejected (%d bytes)\n", index);
    return false;
  }

  // geldig frame → overschrijf actief buffer
  memcpy(imageBuffer, downloadBuffer, sizeof(imageBuffer));
  Serial.println("Frame updated");
  return true;
}

/************ DRAW IMAGE (bovenste helft) ************/
void drawImage() {
  int i = 0;
  for (int y = 0; y < 64; y++) {
    for (int x = 0; x < 64; x++) {
      uint16_t color;
      if (y < 32) {
        // bovenste helft = echte pixels
        color = (imageBuffer[i] << 8) | imageBuffer[i + 1];
        i += 2;
      } else {
        // onderste helft = zwart
        color = 0;
      }
      dma_display->drawPixel(x, y, color);
    }
  }
}

/************ DUMMY FRAME ************/
void drawDummyFrame() {
  for (int y = 0; y < 64; y++) {
    for (int x = 0; x < 64; x++) {
      uint16_t color = (y < 32) ? ((x << 11) & 0xF800) | ((y << 5) & 0x07E0) : 0;
      dma_display->drawPixel(x, y, color);
    }
  }
}


void setup() {

  Serial.begin(115200);

  // WIFI
  WiFi.begin(ssid, password);
  Serial.print("Connecting WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi connected");

  HUB75_I2S_CFG::i2s_pins pins = {R1,   G1,   BL1,  R2,   G2,  BL2, CH_A,
                                  CH_B, CH_C, CH_D, CH_E, LAT, OE,  CLK};

  // Module configuration
  HUB75_I2S_CFG mxconfig(
    PANEL_RES_X,   // module width
    PANEL_RES_Y,   // module height
    PANEL_CHAIN,    // Chain length
    pins
  );

  mxconfig.clkphase = false;

  // Display Setup
  dma_display = new MatrixPanel_I2S_DMA(mxconfig);
  dma_display->begin();
  dma_display->setBrightness8(255); //0-255
  dma_display->clearScreen();

  dma_display->fillScreen(0xFF00);

}

void loop() {
  // probeer frame te vernieuwen
  downloadImageRobust();

  // altijd tekenen (laatste geldige frame)
  drawImage();

  delay(5000);
}
  
