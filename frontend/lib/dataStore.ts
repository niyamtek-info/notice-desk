// lib/dataStore.ts
import fs from 'fs';
import path from 'path';

// Types
interface Lawyer {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  dob: string;
  contact: string;
  email: string;
  address: string;
  barCouncilCode: string;
  barCouncilState: string;
  empanelmentDate?: string;
  empanelmentStatus: string;
  empaneledBranch: string;
  regionalOffice: string;
  zonalOffice: string;
}

interface Valuer {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  authorizationDate: string;
  authorizationBranch: string;
  registrationDetails: string;
  empanelStatus: string;
  empaneledBranch: string;
  regionalOffice: string;
  zonalOffice: string;
  contact: string;
  email: string;
  address: string;
}

interface CA {
  id?: string;
  key: string;
  firstName: string;
  lastName: string;
  contact: string;
  email: string;
  address: string;
  caRegNumber: string;
}

interface DataStore {
  lawyers: Lawyer[];
  valuers: Valuer[];
  cas: CA[];
}

const DATA_FILE_PATH = path.join(process.cwd(), 'data', 'parties.json');

// Default data
const defaultData: DataStore = {
  lawyers: [
    {
      id: "L001",
      key: "L001",
      firstName: "John",
      lastName: "Smith",
      dob: "1985-06-15",
      contact: "+91-9876543210",
      email: "john.smith@lawfirm.com",
      address: "123 Legal Street, Mumbai, Maharashtra",
      barCouncilCode: "MH/2010/12345",
      barCouncilState: "Maharashtra",
      empanelmentDate: "2015-03-20",
      empanelmentStatus: "active",
      empaneledBranch: "Mumbai Central",
      regionalOffice: "Western Region",
      zonalOffice: "Zone 1"
    },
    {
      id: "L002",
      key: "L002",
      firstName: "Priya",
      lastName: "Sharma",
      dob: "1988-09-22",
      contact: "+91-9876543211",
      email: "priya.sharma@advocates.com",
      address: "456 Court Road, Delhi",
      barCouncilCode: "DL/2012/67890",
      barCouncilState: "Delhi",
      empanelmentDate: "2017-07-15",
      empanelmentStatus: "active",
      empaneledBranch: "Delhi High Court",
      regionalOffice: "Northern Region",
      zonalOffice: "Zone 2"
    }
  ],
  valuers: [
    {
      id: "V001",
      key: "V001",
      firstName: "Rajesh",
      lastName: "Kumar",
      authorizationDate: "2018-04-10",
      authorizationBranch: "Chennai Branch",
      registrationDetails: "REG/2018/CV001",
      empanelStatus: "active",
      empaneledBranch: "Chennai Central",
      regionalOffice: "Southern Region",
      zonalOffice: "Zone 3",
      contact: "+91-9876543212",
      email: "rajesh.kumar@valuers.com",
      address: "789 Valuation Plaza, Chennai, Tamil Nadu"
    },
    {
      id: "V002",
      key: "V002",
      firstName: "Meera",
      lastName: "Patel",
      authorizationDate: "2019-11-25",
      authorizationBranch: "Ahmedabad Branch",
      registrationDetails: "REG/2019/CV002",
      empanelStatus: "active",
      empaneledBranch: "Ahmedabad West",
      regionalOffice: "Western Region",
      zonalOffice: "Zone 1",
      contact: "+91-9876543213",
      email: "meera.patel@propertyval.com",
      address: "321 Assessment Avenue, Ahmedabad, Gujarat"
    }
  ],
  cas: [
    {
      id: "C001",
      key: "C001",
      firstName: "Amit",
      lastName: "Agarwal",
      contact: "+91-9876543214",
      email: "amit.agarwal@caoffice.com",
      address: "654 Accountant Street, Bangalore, Karnataka",
      caRegNumber: "ICAI123456"
    },
    {
      id: "C002",
      key: "C002",
      firstName: "Sunita",
      lastName: "Verma",
      contact: "+91-9876543215",
      email: "sunita.verma@auditfirm.com",
      address: "987 Finance Tower, Pune, Maharashtra",
      caRegNumber: "ICAI789012"
    }
  ]
};

// Ensure data directory and file exist
function ensureDataFile() {
  const dataDir = path.dirname(DATA_FILE_PATH);

  // Create data directory if it doesn't exist
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }

  // Create data file with default data if it doesn't exist
  if (!fs.existsSync(DATA_FILE_PATH)) {
    fs.writeFileSync(DATA_FILE_PATH, JSON.stringify(defaultData, null, 2));
  }
}

// Read data from file
export function readData(): DataStore {
  ensureDataFile();
  try {
    const fileContent = fs.readFileSync(DATA_FILE_PATH, 'utf8');
    return JSON.parse(fileContent);
  } catch (error) {
    console.error('Error reading data file:', error);
    // Return default data and recreate file
    writeData(defaultData);
    return defaultData;
  }
}

// Write data to file
export function writeData(data: DataStore): void {
  ensureDataFile();
  try {
    fs.writeFileSync(DATA_FILE_PATH, JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error writing data file:', error);
    throw new Error('Failed to save data');
  }
}

// Helper function to generate unique ID
export function generateId(type: string): string {
  const prefix = type === 'lawyer' ? 'L' : type === 'valuer' ? 'V' : 'C';
  const timestamp = Date.now().toString().slice(-3);
  //   const random = Math.floor(Math.random() * 100).toString().padStart(2, '0');
  return `${prefix}${timestamp}`;
}

// Helper function to determine party type
export function getPartyType(party: unknown): 'lawyer' | 'valuer' | 'ca' {
  const p = party as Record<string, unknown>;
  if (p.barCouncilCode !== undefined) return 'lawyer';
  if (p.registrationDetails !== undefined) return 'valuer';
  return 'ca';
}

// Export types for use in API
export type { Lawyer, Valuer, CA, DataStore };