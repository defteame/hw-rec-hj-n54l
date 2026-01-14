![](_page_0_Picture_0.jpeg)

![](_page_0_Picture_1.jpeg)

# nPM1300

Power Management IC (PMIC) with battery charging, accurate fuel gauging and advanced system management features.

#### **Key benefits**

- Intelligent system management features eliminate need for discrete system management components like dedicated button-reset ICs and external watchdogs
- Ultra low-power, accurate fuel gauging capabilities, for battery state-of-charge monitoring and battery runtime estimation
- USB-C compatible battery charger for single-cell Lithium-ion, Lithium-polymer and Lithium iron phosphate batteries up to 4.45 V.

## **Block diagram**

### nPM1300

![](_page_0_Figure_10.jpeg)

## Overview

nPMI300 is a power management IC (PMIC) that simplifies system design by integrating essential functions required for embedded Bluetooth Low Energy designs. It features hard reset functionality for one or two buttons, accurate battery fuel gauging, system-level watchdog, power loss warning, and recovery from failed boot.

These functions are typically implemented as discrete components in Bluetooth Low Energy (LE) embedded designs, but the nPM1300 integrates them into a single, compact package, simplifying system design and reducing the number of required components.

The nPM1300 is designed to provide highly efficient power regulation for Nordic's nRF52, nRF53 and nRF54 Series System-on-Chips (SoCs), supporting wireless protocols such as Bluetooth Low Energy, LE Audio, Bluetooth mesh, Thread and Zigbee. It is ideal for compact and advanced IoT products such as advanced wearables and portable medical applications. nPM1300 is also suitable for battery charging, fuel gauge and system management in applications based on the nRF91 Series System-in-Packages (SiPs).

#### **Key features**

- Highly efficient PMIC with built-in system management features
  - Accurate fuel gauge with host SoC/MCU
  - Watchdog and boot timer
  - Power loss warning
  - Button hard-reset
- 800 mA battery charger
  - Supports Li-ion, Li-poly and LiFePO, batteries
- Four individually controllable power rails
  - Two highly efficient buck regulators with a 200 mA current limit
  - Two 100 mA load switches or 50 mA LDOs
- Input regulator with USB support
  - USB-C compatible
- Ship- and hibernate modes
- Five GPIOs and three LED drivers
- -40°C to 85°C operating temperature

## **Applications**

- Wearables
- Hand-held entertainment devices
- Personal medical devices
- Rechargeable smart home sensors

## **Specification**

| Battery charger<br>Regulatory compliance<br>Termination voltage<br>Power path<br>Charge current   | JEITA compliant<br>3.5 to 4.45 V<br>Dynamic<br>32 mA to 800 mA        |
|---------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| Input regulator<br>Input voltage<br>Output voltage<br>Overvoltage protection<br>USB current limit | 4.0 to 5.5 V<br>2.3 to 5.5 V unregulated<br>22 V transient<br>1500 mA |
| Buck regulators<br>Output voltage<br>Current limit                                                | 2<br>1.0 - 3.3 V<br>200 mA output each                                |
| Battery voltage                                                                                   | 2.3 V to 4.45 V                                                       |
| Operating temp                                                                                    | -40°C to 85°C                                                         |

![](_page_0_Picture_38.jpeg)