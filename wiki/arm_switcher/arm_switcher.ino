// This code counts rising edges of an input trigger (from camera or stage) and 
// switches analog output voltage setting after every N trigger pulses.
// In this version, analog output is bipolar (-5..5V), by using DAC chip MCP4725, voltage inverter ICL7660S and opAmp UA741. 
// see /wiring_fritzing folder for detals.
// tested on Teensy 2.0, should work on Arduino, too.
// Default speed of Arduino Wire library is 100KHz. The Adafruit MCP4725 library can run at speed 400KHz by setting the TWBR = 12;
// Nikita Vladimirov, 2019.
#include <Wire.h>
#include <Adafruit_MCP4725.h>

const float VCC = 5.0; // power supply voltage. Don't use USB power, it's noisy and can be < 5V.
const float opAmp_gain = 2.0; // multiplication factor of the opAmp, equal to 1 + R1/R2, where R1, R2 are resistor values.
const byte interruptPin = 7; // Teensy 2.0, interrupt pins are: 5, 6, 7, 8. This digital pin must be capable of Interrupt mode.
const byte ledPin = 11; // blink every time a pulse is detected
const char _version[16] = "2019.11.01";

volatile int counter;
volatile int counter_old;
volatile byte ledState;
Adafruit_MCP4725 dac; // constructor
float voltage_out_0 = -0.42;
float voltage_out_1 = 0.35;
int n_pulses_switch_period = 10; // DAC output will alternate between voltage_out_0 and voltage_out_1 with this period
uint16_t dac_value; 
uint16_t dac_value_0; 
uint16_t dac_value_1; 
  
void setup() {
  Serial.begin(9600);
  pinMode(ledPin, OUTPUT);
  digitalWrite(ledPin, HIGH);
  ledState = LOW;
  
  pinMode(interruptPin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(interruptPin), count, RISING);
  counter = 0;
  counter_old = 0;
  
  dac.begin(0x62); // if unsure, use I2C scanner to find the I2C address of your MCP4725: http://henrysbench.capnfatz.com/henrys-bench/arduino-projects-tips-and-more/arduino-quick-tip-find-your-i2c-address/
  dac_value_0 = volts2dac_value(voltage_out_0);
  dac_value_1 = volts2dac_value(voltage_out_1);
  dac_value = dac_value_0;
}

void loop() {
  if(counter > counter_old){
    Serial.println(counter);
    counter_old = counter;
    digitalWrite(ledPin, ledState);
    if(counter_old % n_pulses_switch_period == 0){
      if(dac_value == dac_value_0) dac_value = dac_value_1;
      else dac_value = dac_value_0;
    }
  }
  dac.setVoltage(dac_value, false); // this command should always run as fast as possible, since it doesn't hold the value.
  readCommand();
}

void count() {
  counter++;
  ledState = !ledState;
}

uint16_t volts2dac_value(float volts_out){
  // return(int(volts_out / VCC * 4095.0)); //unipolar case, no amplifier
  float v_dac;
  v_dac = (volts_out + VCC) / opAmp_gain;
  return(int(v_dac / VCC * 4095.0));
}

void readCommand() {
    boolean newCommandReceived = false;
    char receivedChars[16];
    char rc;
    byte ic = 0;
    while (Serial.available() > 0  && newCommandReceived == false)
    {
      rc = Serial.read();
      receivedChars[ic] = rc;
      ic++;
      delay(2);  //slow looping to allow buffer to fill with next character
      if(rc == '\n' || rc == '\r'){
        newCommandReceived = true;
        receivedChars[ic] = '\0';
      }
    }
    if(newCommandReceived){
      parseCommand(receivedChars);
    }
}

void parseCommand(char receivedChars[]){
  char *keywordString;
  char *token;
  
  keywordString = strstr(receivedChars, "n ");
  if (keywordString != NULL){ // set the switching period
    token = strtok(keywordString," "); //chop the keyword
    token = strtok(NULL, "\n"); //get the number
    n_pulses_switch_period = atoi(token);
    Serial.println(n_pulses_switch_period);
  }
  
  keywordString = strstr(receivedChars, "?n");
  if (keywordString != NULL){
    Serial.println(n_pulses_switch_period);
  }

  keywordString = strstr(receivedChars, "?ver");
  if (keywordString != NULL){
    Serial.println(_version);
  }
  
  keywordString = strstr(receivedChars, "reset");
  if (keywordString != NULL){
    counter = 0;
    counter_old = 0;
    dac_value = dac_value_0;
    Serial.println(counter);
  }
  
  keywordString = strstr(receivedChars, "v0 ");
  if (keywordString != NULL){
    token = strtok(keywordString," "); //chop the keyword
    token = strtok(NULL, "\n"); //get the number
    voltage_out_0 = atof(token);
    dac_value_0 = volts2dac_value(voltage_out_0);
    Serial.println(voltage_out_0);
  }

  keywordString = strstr(receivedChars, "v1 ");
  if (keywordString != NULL){
    token = strtok(keywordString," "); //chop the keyword
    token = strtok(NULL, "\n"); //get the number
    voltage_out_1 = atof(token);
    dac_value_1 = volts2dac_value(voltage_out_1);
    Serial.println(voltage_out_1);
  }
}

