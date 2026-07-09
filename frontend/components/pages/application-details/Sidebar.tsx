import React, { useState } from "react";
import { IoDocumentTextOutline } from "react-icons/io5";
import { TbLayoutSidebarLeftCollapse, TbChevronDown, TbChevronRight } from "react-icons/tb";

interface SidebarProps {
    activeItem: string;
    onSelect: (item: string) => void;
}

interface MenuItem {
    id: string;
    label: string;
    isAccordion: boolean;
    subItems?: string[];
}

const menuItems: (string | MenuItem)[] = [
    {
        id: "loan-application",
        label: "Loan Application",
        isAccordion: true,
        subItems: [
            "Loan Details",
            "13.2 Details",
            "13.4 Details",
            "Symbolic Vacation",
            "CJM Details",
            "Physical Possession",
            "Auction Notice",
            "Auction Portal",
            "Post Sale Details",
            "Sale Certificate",
            "Niyamtek Remarks"
        ]
    },
    // {
    //     id: "reports",
    //     label: "Reports",
    //     isAccordion: false
    // }
];

const Sidebar: React.FC<SidebarProps> = ({ activeItem, onSelect }) => {
    const [expandedItems, setExpandedItems] = useState<string[]>(["loan-application"]);

    // Set default active item to "Loan Details" if "Loan Application" is expanded
    React.useEffect(() => {
        if (activeItem === "Loan Application" || !activeItem) {
            onSelect("Loan Details");
        }
    }, [activeItem]);

    const toggleAccordion = (itemId: string) => {
        setExpandedItems(prev => {
            if (prev.includes(itemId)) {
                // If already expanded, close it
                return prev.filter(id => id !== itemId);
            } else {
                // Close all other accordions and expand only this one
                return [itemId];
            }
        });
    };

    const handleSelect = (item: string, isSubItem: boolean = false) => {
        onSelect(item);
        // Only close accordions when clicking regular items (non-accordion items)
        if (!isSubItem && !item.includes("Application") && !item.includes("Reports")) {
            setExpandedItems([]);
        }
    };

    const isActive = (item: string) => activeItem === item;

    const isParentActive = (itemId: string) => {
        const menuItem = menuItems.find(m => typeof m === 'object' && m.id === itemId) as MenuItem | undefined;
        if (!menuItem || !menuItem.isAccordion || !menuItem.subItems) return false;

        return menuItem.subItems.some(subItem => isActive(subItem));
    };

    const isParentOrSubActive = (menuItem: MenuItem) => {
        return isActive(menuItem.label) || isParentActive(menuItem.id);
    };

    return (
        <div className="bg-white rounded-lg shadow-sm p-6 h-full w-full flex-shrink-0 flex flex-col overflow-hidden">
            <div className="flex items-center justify-between px-2 mb-4 flex-shrink-0">
                <h2 className="text-lg font-bold text-gray-800">Work Items</h2>
            </div>

            <ul className="space-y-2 flex-1 overflow-y-auto pr-1">
                {menuItems.map((menuItem) => {
                    if (typeof menuItem === 'string') {
                        // Regular menu item
                        const itemActive = isActive(menuItem);
                        return (
                            <li key={menuItem}>
                                <button
                                    onClick={() => handleSelect(menuItem)}
                                    className={`w-full mb-3 text-left flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 cursor-pointer group
                                        ${itemActive
                                            ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg font-semibold"
                                            : "text-gray-700 hover:bg-blue-50 hover:text-gray-800 hover:shadow-md"
                                        }`}
                                >
                                    <span className="font-medium">{menuItem}</span>
                                </button>
                            </li>
                        );
                    } else {
                        // Accordion menu item
                        const menuItemTyped = menuItem as MenuItem;
                        const isExpanded = expandedItems.includes(menuItemTyped.id);
                        const parentOrSubActive = isParentOrSubActive(menuItemTyped);

                        return (
                            <li key={menuItemTyped.id} className="space-y-1 mb-3">
                                {/* Parent button */}
                                <button
                                    onClick={() => {
                                        toggleAccordion(menuItemTyped.id);
                                        onSelect(menuItemTyped?.label == "Loan Application" ? "Loan Details" : menuItemTyped?.label);
                                    }}
                                    className={`w-full text-left flex items-center gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 cursor-pointer group sticky top-0 z-10
                                        ${parentOrSubActive
                                            ? "bg-gradient-to-r from-blue-600 to-blue-700 text-white shadow-lg font-semibold"
                                            : "bg-white text-gray-700 hover:bg-blue-50 hover:text-gray-800 hover:shadow-md"
                                        }`}
                                >
                                    <span className="font-medium flex-1">{menuItemTyped.label}</span>
                                    {menuItemTyped.subItems && menuItemTyped.subItems.length > 0 && (
                                        <div className={`flex items-center justify-center w-6 h-6 rounded-full transition-all duration-200
                                            ${parentOrSubActive
                                                ? "bg-white/20"
                                                : "group-hover:bg-blue-100"
                                            }`}>
                                            {isExpanded ? (
                                                <TbChevronDown size={16} className={`transition-transform duration-200 ${parentOrSubActive ? "text-white" : "text-gray-600"}`} />
                                            ) : (
                                                <TbChevronRight size={16} className={`transition-transform duration-200 ${parentOrSubActive ? "text-white" : "text-gray-600"}`} />
                                            )}
                                        </div>
                                    )}
                                </button>

                                {/* Sub-items */}
                                <div className={`overflow-hidden transition-all duration-300 ease-in-out ${isExpanded ? "max-h-1000 opacity-100" : "max-h-0 opacity-0"
                                    }`}>
                                    <ul style={{ listStyle: "none", paddingLeft: 0 }} className="ml-6 space-y-1 border-gray-100 pl-1 mt-2 list-none">
                                        {menuItemTyped.subItems?.map((subItem, index) => {
                                            const subItemActive = isActive(subItem);
                                            // Color mapping for each sub-item index
                                            const colorClasses = [
                                                { active: "text-blue-600", inactive: "text-gray-500", hover: "group-hover:text-blue-600" },
                                                { active: "text-green-600", inactive: "text-gray-500", hover: "group-hover:text-green-600" },
                                                { active: "text-purple-600", inactive: "text-gray-500", hover: "group-hover:text-purple-600" },
                                                { active: "text-orange-600", inactive: "text-gray-500", hover: "group-hover:text-orange-600" },
                                                { active: "text-red-600", inactive: "text-gray-500", hover: "group-hover:text-red-600" },
                                            ];
                                            const colorClass = colorClasses[index % colorClasses.length];

                                            return (
                                                <li key={subItem}>
                                                    <button
                                                        onClick={() => handleSelect(subItem, true)}
                                                        className={`w-full text-left flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-200 cursor-pointer text-sm group
                                                            ${subItemActive
                                                                ? "bg-blue-50 text-blue-700 font-medium border border-blue-200"
                                                                : "text-gray-600 hover:bg-blue-50 hover:text-gray-800"
                                                            }`}
                                                    >
                                                        <span className={`${subItemActive ? colorClass.active : colorClass.inactive} ${!subItemActive ? colorClass.hover : ''}`}>
                                                            <IoDocumentTextOutline />
                                                        </span>
                                                        {subItem}
                                                    </button>
                                                </li>
                                            );
                                        })}
                                    </ul>
                                </div>
                            </li>
                        );
                    }
                })}
            </ul>
        </div>
    );
};

export default Sidebar;