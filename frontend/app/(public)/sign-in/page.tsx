"use client";

import React, { useState } from "react";
import { Form, Input, Button, Card, Typography, message, Alert } from "antd";
import { UserOutlined, LockOutlined } from "@ant-design/icons";
import { useRouter } from "next/navigation";
import { LoginApi } from "@/src/services/LoginApi";
import { FaRegUser } from "react-icons/fa6";
import logo from "@/images/niyamtek.png"
import Image from "next/image";


const { Title, Text } = Typography;

export default function SignInPage() {
    const router = useRouter();
    const [loading, setLoading] = useState(false);
    const [errorMsg, setErrorMsg] = useState<string | null>(null);


    // ...

    const onFinish = async (values: any) => {
        setLoading(true);
        setErrorMsg(null); // Clear previous errors
        try {
            const data = await LoginApi.login(values);

            // Store token in localStorage or cookie
            localStorage.setItem("token", data.access_token);
            message.success("Login successful!");
            router.push("/dashboard");
        } catch (error: any) {
            console.error("Login error:", error);

            let serverMessage = "Something went wrong. Please try again later.";

            // Axios-style error handling
            if (error?.response) {
                // Server responded with status code
                const status = error.response.status;

                if (status === 401) {
                    serverMessage = "Login failed. Please check your credentials.";
                } else if (status === 500) {
                    serverMessage = "Server error. Please try again later.";
                } else {
                    serverMessage =
                        error.response.data?.message ||
                        "Unexpected server error occurred.";
                }
            } else if (error?.request) {
                // Request sent but no response
                serverMessage = "Server is unreachable. Please check your internet.";
            }

            setErrorMsg(serverMessage);
            message.error(serverMessage);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            display: "flex",
            justifyContent: "center",
            alignItems: "center",
            minHeight: "100vh",
            background: "#f0f2f5"
        }}>
            <Card style={{ width: 450, boxShadow: "0 4px 12px rgba(0,0,0,0.1)" }}>
                <div style={{ textAlign: "center", marginBottom: 20 }}>
                    <div className="flex items-center justify-center mb-4 mt-3">
                        {/* <div className="border-[1px] rounded-full p-2 text-gray-500">
                            <FaRegUser className="text-[17px]" />
                        </div> */}
                        <Image alt="company_logo" src={logo} width={150} height={150} />
                    </div>
                    {/* <Title level={3} className="!mb-1 !font-bold">Welcome</Title> */}
                    <Text type="secondary">Welcome Please sign in to continue</Text>
                </div>

                {errorMsg && (
                    <Alert
                        message={errorMsg}
                        type="error"
                        showIcon
                        closable
                        className="!mb-6"
                        onClose={() => setErrorMsg(null)}
                    />
                )}

                <Form 
                    name="login_form"
                    initialValues={{ remember: true }}
                    onFinish={onFinish}
                    layout="vertical"
                    size="large"
                >
                    <Form.Item
                        label="Email"
                        name="email"
                        className="!mb-7"
                        rules={[
                            { required: true, message: "Please enter your Email!" },
                            { type: "email", message: "Please enter a valid email!" }
                        ]}
                    >
                        <Input
                            prefix={<UserOutlined />}
                            placeholder="Please enter your email"
                            className="!py-2.5"
                        />
                    </Form.Item>

                    <Form.Item
                        label="Password"
                        name="password"
                        className="!mb-7"
                        rules={[{ required: true, message: "Please enter your Password!" }]}
                    >
                        <Input.Password
                            prefix={<LockOutlined />}
                            placeholder="Please enter your password"
                            className="!py-2.5"
                        />
                    </Form.Item>

                    <Form.Item >
                        <Button className="!mt-3 !h-[45px]" type="primary" htmlType="submit" block loading={loading}>
                            Sign In
                        </Button>
                    </Form.Item>
                </Form>
            </Card>
        </div>
    );
}
